"""Phase-9 hand calculations, causal forecasts, rejection and risk parity."""
from dataclasses import asdict,replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
import inspect,json,math,tempfile,unittest
import numpy as np
from portfolio_fx.report import fixture
from portfolio_fx.contracts import FXConfig,ExecutionConfig
from portfolio_fx_risk.contracts import RiskConfig,VolatilityConfig,Capacity
from portfolio_fx_risk import engine as old_ledger
from portfolio_regimes.contracts import RegimeConfig
from portfolio_econometrics.contracts import EconometricConfig,Rejected,MODELS
from portfolio_econometrics.linear import least_squares,stable,estimate as linear
from portfolio_econometrics.kalman import update,estimate as kalman
from portfolio_econometrics.markov import mixture
from portfolio_econometrics.forecast import forecast
from portfolio_econometrics.plans import direction,propose
from portfolio_econometrics.evaluation import error_metrics,evaluate
from portfolio_econometrics.workflow import bundle,replay
from portfolio_econometrics.audit import encoded
from portfolio_econometrics import ledger


class EquationTests(unittest.TestCase):
    def test_ols_hand_parameters_and_residual_variance(self):
        beta,cov,_=least_squares(np.array([[1,-1],[1,0],[1,1]]),np.array([[1],[0],[3]]),1e6)
        np.testing.assert_allclose(beta[:,0],[4/3,1]); self.assertAlmostEqual(cov[0,0],8/3)
        self.assertAlmostEqual(float((np.array([1,2])@beta)[0]),10/3)

    def test_ar_hand_recursion(self):
        r=[.01]
        for _ in range(59): r.append(.001+.5*r[-1])
        value=linear(r,None,'ar',EconometricConfig())
        self.assertAlmostEqual(value['mean'],.001+.5*r[-1]); self.assertAlmostEqual(value['diagnostics']['spectral_radius'],.5)

    def test_arimax_known_exogenous_lag(self):
        x=[.001*math.sin(i) for i in range(60)]; r=[.01]
        for i in range(59): r.append(.001+.4*r[-1]+2*x[i])
        value=linear(r,x,'arimax',EconometricConfig())
        self.assertAlmostEqual(value['mean'],.001+.4*r[-1]+2*x[-1])

    def test_var_hand_matrix(self):
        a=np.array([[.5,.2],[-.1,.3]]); c=np.array([.001,.002]); values=[np.array([.01,.02])]
        for _ in range(59): values.append(c+a@values[-1])
        value=linear([r[0] for r in values],[r[1] for r in values],'var',EconometricConfig())
        self.assertAlmostEqual(value['mean'],(c+a@values[-1])[0]); self.assertLess(value['diagnostics']['spectral_radius'],1)

    def test_singular_and_unstable_rejection(self):
        with self.assertRaises(Rejected): least_squares(np.ones((5,2)),np.ones((5,1)),1e6)
        with self.assertRaises(Rejected): stable(np.array([[1.01]]),.995)
        self.assertAlmostEqual(stable(np.array([[.5,0],[0,-.8]]),.995),.8)

    def test_explosive_ar_rejected(self):
        r=[.001]
        for _ in range(59): r.append(.00001+1.01*r[-1])
        with self.assertRaisesRegex(Rejected,'unstable'): linear(r,None,'ar',EconometricConfig())

    def test_kalman_scalar_by_hand(self):
        state,cov,s=update(np.array([0.]),np.array([[1.]]),np.array([1.]),2.,0.,1.)
        self.assertAlmostEqual(state[0],1); self.assertAlmostEqual(cov[0,0],.5); self.assertEqual(s,2.)
        state,cov,s=update(np.array([0.]),np.array([[1.]]),np.array([1.]),2.,1.,1.)
        self.assertAlmostEqual(state[0],4/3); self.assertAlmostEqual(cov[0,0],2/3); self.assertEqual(s,3.)

    def test_kalman_vector_covariance_by_hand(self):
        state,cov,s=update(np.zeros(2),np.eye(2),np.ones(2),3.,0.,1.)
        np.testing.assert_allclose(state,[1.,1.]); np.testing.assert_allclose(cov,[[2/3,-1/3],[-1/3,2/3]]); self.assertEqual(s,3)
        with self.assertRaises(ValueError): update(np.zeros(2),np.array([[1,2],[2,1]]),np.ones(2),3.,0.,1.)

    def test_mixture_total_variance_by_hand(self):
        mean,var=mixture([.25,.75],[0.,.02],[.0001,.0004])
        self.assertAlmostEqual(mean,.015); self.assertAlmostEqual(var,.0004)
        with self.assertRaises(ValueError): mixture([.5,.7],[0.,1.],[1.,1.])

    def test_cost_hurdle_by_hand(self):
        execution=ExecutionConfig(commission_bps=1,half_spread_bps=1,slippage_bps=1,long_carry_annual_rate=0,short_carry_annual_rate=0)
        cfg=EconometricConfig(signal_buffer=.0001)
        self.assertEqual(direction(.0006,execution,RiskConfig(),cfg)[0],0)
        side,threshold=direction(-.001,execution,RiskConfig(),cfg)
        self.assertEqual(side,-1); self.assertAlmostEqual(threshold,.0007)

    def test_errors_and_paired_baseline_by_hand(self):
        m=error_metrics([dict(actual=.01,predicted=.02),dict(actual=-.01,predicted=0.)])
        self.assertAlmostEqual(m['mae'],.01); self.assertAlmostEqual(m['rmse'],.01)
        self.assertAlmostEqual(m['paired_no_change_mse'],.0001); self.assertAlmostEqual(m['mse_skill_vs_no_change'],0.)
        self.assertEqual(m['directional_accuracy'],.5); self.assertEqual(error_metrics([])['n'],0)

    def test_config_rejects_invalid_settings(self):
        for kwargs in ({'window':True},{'window':20},{'maximum_root':1},{'kalman_process_variance':float('nan')},{'markov_states':4},{'minimum_forecast_coverage':2}):
            with self.assertRaises(ValueError): EconometricConfig(**kwargs)


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows,cls.rates=fixture(); cls.time=cls.rows[13*48-1].end

    def test_all_models_share_interface(self):
        for model in MODELS:
            with self.subTest(model=model):
                r=forecast(self.rows,self.rates,self.time,model)['payload']
                self.assertEqual(r['status'],'DISABLED' if model=='vecm' else 'READY')
                self.assertFalse(r['executable']); self.assertEqual(r['decision_time'],self.time.isoformat())

    def test_future_suffix_invariance_all_models(self):
        changed=tuple(replace(r,open=r.open*2,high=r.high*2,low=r.low*2,close=r.close*2) if r.end>self.time else r for r in self.rows)
        rates=tuple(replace(r,value=r.value+.1) if r.available_at>self.time else r for r in self.rates)
        for model in MODELS:
            self.assertEqual(forecast(changed,rates,self.time,model),forecast(self.rows,self.rates,self.time,model))

    def test_late_revision_not_visible(self):
        old=self.rows[13*48-1]; later=self.time+timedelta(hours=1)
        revision=replace(old,open=old.open*2,high=old.high*2,low=old.low*2,close=old.close*2,ingested_at=later,available_at=later)
        self.assertEqual(forecast(self.rows+(revision,),self.rates,self.time,'ar'),forecast(self.rows,self.rates,self.time,'ar'))

    def test_macro_availability_at_each_historical_bar(self):
        r=forecast(self.rows,self.rates,self.time,'arimax')['payload']
        for snapshot in r['inputs']['rate_snapshots']:
            for key in ('eur','usd'): self.assertLessEqual(snapshot[key]['available_at'].isoformat(),snapshot['time'])
        past=tuple(r for r in self.rates if r.available_at<=self.time)
        delayed=tuple(replace(r,ingested_at=self.time,available_at=self.time) for r in past)
        self.assertEqual(forecast(self.rows,delayed,self.time,'arimax')['payload']['status'],'UNAVAILABLE')

    def test_missing_macro_does_not_block_univariate(self):
        for m in ('arimax','var'): self.assertEqual(forecast(self.rows,(),self.time,m)['payload']['status'],'UNAVAILABLE')
        self.assertEqual(forecast(self.rows,(),self.time,'ar')['payload']['status'],'READY')

    def test_constant_macro_rejected_without_fake_features(self):
        rates=tuple(replace(r,value=.03) for r in self.rates)
        self.assertEqual(forecast(self.rows,rates,self.time,'var')['payload']['reason'],'degenerate_training_feature')

    def test_stale_and_insufficient_data_abstain(self):
        self.assertEqual(forecast((),(),self.time,'ar')['payload']['status'],'UNAVAILABLE')
        r=forecast(self.rows[:13*48],self.rates,self.time+timedelta(days=3),'ar')['payload']
        self.assertEqual(r['reason'],'stale_training_data')

    def test_markov_nonconvergence_rejected(self):
        r=forecast(self.rows,self.rates,self.time,'markov_switching',EconometricConfig(markov_iterations=2))['payload']
        self.assertEqual(r['status'],'REJECTED'); self.assertIsNone(r['mean'])

    def test_markov_prediction_transitions_before_next_mean(self):
        r=forecast(self.rows,self.rates,self.time,'markov_switching')['payload']; fit=r['parameters']
        p=np.array(fit['last_filtered'])@np.array(fit['transition'])
        np.testing.assert_allclose(p,r['diagnostics']['predictive_probabilities'])
        self.assertAlmostEqual(r['mean'],p@np.array(fit['return_means']))

    def test_arimax_var_first_equation_consistency(self):
        a=forecast(self.rows,self.rates,self.time,'arimax')['payload']; v=forecast(self.rows,self.rates,self.time,'var')['payload']
        self.assertAlmostEqual(a['mean'],v['mean']); self.assertAlmostEqual(a['variance'],v['variance'])

    def test_forecast_guard_and_kill_switch(self):
        r=forecast(self.rows,self.rates,self.time,'ar',EconometricConfig(maximum_forecast_sigma=.00001))['payload']
        self.assertEqual(r['status'],'REJECTED')
        fake=dict(payload=dict(decision_time=self.time.isoformat(),status='READY',mean=.01,reason='test'))
        with patch('portfolio_econometrics.plans.forecast',return_value=fake):
            p=propose(self.rows,self.rates,self.time,'ar',Capacity(10000,1000),risk=RiskConfig(kill_switch=True))
        self.assertEqual(p['payload']['sizing']['state'],'NO_TRADE')

    def test_forecast_bundle_replay_and_integrity(self):
        request=dict(candles=[asdict(r) for r in self.rows],rates=[asdict(r) for r in self.rates],time=self.time,model='ar',econometrics=asdict(EconometricConfig()))
        doc=bundle(request,'forecast')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'forecast.json'; path.write_bytes(encoded(doc)); self.assertEqual(replay(path)['status'],'verified')
            doc['payload']['result']['payload']['mean']=99; path.write_bytes(encoded(doc))
            with self.assertRaises(ValueError): replay(path)

    def test_risk_ledger_body_preserved(self):
        new=inspect.getsource(ledger.run).replace(', proposal_factory: Callable=propose','').replace('pending=proposal_factory(','pending=propose(')
        self.assertEqual(new,inspect.getsource(old_ledger.run))
        self.assertEqual(inspect.getsource(ledger.barrier),inspect.getsource(old_ledger.barrier))

    def test_no_change_ledger_and_evaluation(self):
        start=self.rows[12*48].start; end=self.rows[13*48-1].end
        request=dict(candles=[asdict(r) for r in self.rows],rates=[asdict(r) for r in self.rates],model='no_change',start=start,end=end,
                     econometrics=asdict(EconometricConfig()),features=asdict(FXConfig()),execution=asdict(ExecutionConfig()),
                     risk=asdict(RiskConfig()),volatility=asdict(VolatilityConfig()),fx_capital_fraction=.1,regimes=asdict(RegimeConfig()))
        body=bundle(request)['payload']; old=old_ledger.run(self.rows,self.rates,'no_trade',start,end)
        self.assertEqual(body['result']['totals'],old['totals']); self.assertEqual(body['result']['events'],old['events'])
        self.assertEqual(body['metrics']['completed_trades'],0); self.assertEqual(body['evaluation']['coverage'],1.)
        self.assertEqual(body['evaluation']['forecast_metrics']['n'],5)
        self.assertTrue(all(r['decision_time']<r['label_end']<=end.isoformat() for r in body['evaluation']['observations']))
        ev=evaluate(body['result'],self.rows,{**body['metrics'],'maximum_drawdown':.9},EconometricConfig(),RegimeConfig())
        self.assertEqual(ev['research_status'],'REJECTED')
        self.assertFalse(ev['economic_promotion'])

if __name__=='__main__': unittest.main()
