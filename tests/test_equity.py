"""Phase-4 sourced example, hand calculations and point-in-time checks."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import unittest
import numpy as np

from portfolio_equity.contracts import EquityConfig,Universe,ReturnRow,View
from portfolio_equity.math import optimize,project_capped_simplex
from portfolio_equity.models import equilibrium,posterior,confidence_variance,estimate_covariance
from portfolio_equity.pipeline import allocate,returns_from_prices
from portfolio_equity.rebalance import Account,RebalancePlan,schedule,execute
from portfolio_data.contracts import Datum

TIME=datetime(2020,1,28,16,tzinfo=timezone.utc)
SIGMA=np.diag([.04,.09])
CFG=EquityConfig(minimum_observations=2,commission_bps=0,half_spread_bps=0,slippage_bps=0)


def universe():
    return Universe(("A","B"),"EUR",(.6,.4),TIME-timedelta(days=30),"synthetic chosen reference")


def rows(count=6):
    values=((.01,.02),(-.01,.01),(.02,-.01),(-.02,-.02),(.01,-.01),(-.01,.02))
    return tuple(ReturnRow(TIME+timedelta(days=i),TIME+timedelta(days=i),values[i%6],"synthetic") for i in range(count))


class BlackLittermanTests(unittest.TestCase):
    def test_equilibrium_hand(self):
        np.testing.assert_allclose(equilibrium(SIGMA,(.6,.4),2.5),(.06,.09))

    def test_absolute_view_hand(self):
        r=posterior(SIGMA,(.06,.09),.05,[[1,0]],[.10],[[.002]])
        np.testing.assert_allclose(r.mean,(.08,.09))
        np.testing.assert_allclose(r.mean_covariance,np.diag([.001,.0045]))
        np.testing.assert_allclose(r.predictive_covariance,np.diag([.041,.0945]))

    def test_no_views_exact(self):
        r=posterior(SIGMA,(.06,.09),.05,np.empty((0,2)),[],np.empty((0,0)))
        self.assertEqual(r.mean,(.06,.09))
        np.testing.assert_allclose(r.mean_covariance,.05*SIGMA)

    def test_relative_confidence_interpolation(self):
        for confidence in (.1,.5,.9,1):
            variance=confidence_variance(SIGMA,[1,-1],.05,confidence)
            r=posterior(SIGMA,(.06,.09),.05,[[1,-1]],[.02],[[variance]])
            self.assertAlmostEqual(r.mean[0]-r.mean[1],(1-confidence)*(-.03)+confidence*.02)

    def test_confidence_and_opinion_direction(self):
        means=[]
        for c in (.1,.5,.9):
            variance=confidence_variance(SIGMA,[1,0],.05,c)
            means.append(posterior(SIGMA,(.06,.09),.05,[[1,0]],[.1],[[variance]]).mean[0])
        self.assertLess(means[0],means[1]); self.assertLess(means[1],means[2])
        bearish=posterior(SIGMA,(.06,.09),.05,[[1,0]],[-.1],[[.002]])
        self.assertLess(bearish.mean[0],.06)

    def test_published_idzorek_table6(self):
        f=json.loads((Path(__file__).parent/'fixtures/idzorek_2004.json').read_text())
        p=np.array(f['P']); s=np.array(f['covariance'])
        omega=np.diag(np.diag(p@(f['tau']*s)@p.T))
        r=posterior(s,f['prior'],f['tau'],p,f['Q'],omega)
        np.testing.assert_allclose(r.mean,f['published_posterior'],atol=f['rounding_tolerance_mean'],rtol=0)

    def test_tau_cancels_for_scaled_omega(self):
        answers=[]
        for tau in (.025,15):
            omega=confidence_variance(SIGMA,[1,0],tau,.5)
            answers.append(posterior(SIGMA,(.06,.09),tau,[[1,0]],[.1],[[omega]]).mean)
        np.testing.assert_allclose(*answers)

    def test_invalid_covariance_and_views_fail_closed(self):
        for bad in ([[1,2],[2,1]],[[1,0],[0,0]],[[1,.1],[0,1]]):
            with self.assertRaises(ValueError): equilibrium(bad,(.5,.5),2.5)
        with self.assertRaises(ValueError): posterior(SIGMA,(.06,.09),.05,[[1,0],[1,0]],[.1,.2],np.zeros((2,2)))
        with self.assertRaises(ValueError): posterior(SIGMA,(.06,.09),.05,[[1,0]],[.1],[[-1]])
        with self.assertRaises(ValueError): equilibrium(SIGMA,(1,1),2.5)


class CovarianceTests(unittest.TestCase):
    def test_sample_hand_and_annualization(self):
        result=estimate_covariance([[.01,.02],[-.01,0]],'sample',10)
        np.testing.assert_allclose(result.matrix,[[.002,.002],[.002,.002]])

    def test_ewma_hand(self):
        result=estimate_covariance([[.1,.2],[-.1,0]],'ewma',1,.5)
        np.testing.assert_allclose(result.matrix,[[.01,.01],[.01,.02]])

    def test_ledoit_wolf_hand(self):
        result=estimate_covariance([[.01,0],[-.01,0],[0,.02],[0,-.02]],'ledoit_wolf',1)
        self.assertAlmostEqual(result.shrinkage,17/18)
        np.testing.assert_allclose(result.matrix,np.diag([29/24,31/24])*1e-4)

    def test_centering_translation_invariance(self):
        x=np.array([[.01,0],[-.01,0],[0,.02],[0,-.02]])
        for method in ('sample','ledoit_wolf'):
            np.testing.assert_allclose(estimate_covariance(x,method).matrix,estimate_covariance(x+.1,method).matrix)

    def test_constant_data_and_invalids(self):
        self.assertEqual(estimate_covariance([[1,1],[1,1]]).shrinkage,0)
        for data in ([[1]],[[float('nan'),1],[1,1]]):
            with self.assertRaises(ValueError): estimate_covariance(data)
        with self.assertRaises(ValueError): estimate_covariance([[1],[2]],'ewma',1,1)


class OptimizerTests(unittest.TestCase):
    def test_no_view_recovers_reference(self):
        mu=equilibrium(SIGMA,(.6,.4),2.5)
        result=optimize(mu,SIGMA,2.5,[1,1])
        np.testing.assert_allclose(result.weights,(.6,.4),atol=1e-7)
        self.assertLessEqual(result.optimality_gap,1e-10)

    def test_binding_asset_cap(self):
        result=optimize([1,0],np.eye(2),1,[.6,.6])
        np.testing.assert_allclose(result.weights,[.6,.4])

    def test_two_asset_analytic_optimum(self):
        # f derivative: .04-(.04*w-.09*(1-w))=0 -> w=1.
        result=optimize([.1,.06],SIGMA,1,[1,1])
        # Strong convexity bounds weight error by sqrt(2*objective_gap/lambda_min).
        self.assertLessEqual(np.linalg.norm(np.array(result.weights)-[1,0]),np.sqrt(2e-10/.04))
        symmetric=optimize([.05,.05],np.eye(2)*.04,2,[1,1])
        np.testing.assert_allclose(symmetric.weights,[.5,.5])

    def test_projection_hand(self):
        np.testing.assert_allclose(project_capped_simplex([2,0],[.7,.7]),[.7,.3])

    def test_infeasible_and_nonconverged(self):
        with self.assertRaises(ValueError): optimize([1,0],SIGMA,1,[.4,.4])
        with self.assertRaises(ValueError): optimize([.06,.09],SIGMA,2.5,[1,1],max_iterations=1)


class PipelineTests(unittest.TestCase):
    def test_causal_prefix_and_future_views(self):
        history=rows(); time=history[3].observation_time
        a=allocate(universe(),history,(),time,CFG)
        b=allocate(universe(),history[:4],(),time,CFG)
        self.assertEqual(a,b)
        view=View('late',(1,0),.1,.5,time+timedelta(seconds=1),'fixture')
        with self.assertRaises(ValueError): allocate(universe(),history,(view,),time,CFG)

    def test_universe_history_and_view_vintages(self):
        history=rows(); time=history[-1].observation_time
        with self.assertRaises(ValueError): allocate(replace(universe(),available_at=time+timedelta(days=1)),history,(),time,CFG)
        late=tuple(replace(r,available_at=time+timedelta(days=1)) for r in history)
        with self.assertRaises(ValueError): allocate(universe(),late,(),time,CFG)
        with self.assertRaises(ValueError): allocate(universe(),history,(),time+timedelta(days=10),CFG)
        stale=View('old',(1,0),.1,.5,time-timedelta(days=100),'fixture')
        with self.assertRaises(ValueError): allocate(universe(),history,(stale,),time,CFG)

    def test_zero_confidence_disabled_and_duplicate_rejected(self):
        history=rows(); time=history[-1].observation_time
        view=View('disabled',(1,0),100,0,time,'fixture')
        a=allocate(universe(),history,(view,),time,CFG)
        np.testing.assert_allclose(a['posterior']['mean'],a['prior'])
        self.assertEqual(a['active_view_ids'],[])
        with self.assertRaises(ValueError): allocate(universe(),history,(view,view),time,CFG)

    def test_constraints_hold_for_all_estimators(self):
        for method in ('sample','ewma','ledoit_wolf'):
            result=allocate(universe(),rows(),(),rows()[-1].observation_time,replace(CFG,covariance_method=method))
            w=np.array(result['optimizer']['weights'])
            self.assertTrue((w>=0).all()); self.assertTrue((w<=.6+1e-10).all())
            self.assertAlmostEqual(w.sum(),1)

    def test_configuration_and_view_errors(self):
        for changes in ({'tau':0},{'minimum_observations':1},{'lookback':1},{'risk_aversion':float('nan')},{'max_asset_weight':1.1},{'periods_per_year':True},{'commission_bps':10000}):
            with self.assertRaises(ValueError): replace(CFG,**changes)
        with self.assertRaises(ValueError): View('bad',(1,1),.1,.5,TIME,'fixture')
        with self.assertRaises(ValueError): Universe(('A','A'),'EUR',(.5,.5),TIME,'fixture')
        with self.assertRaises(ValueError): allocate(universe(),rows()[::-1],(),rows()[-1].observation_time,CFG)

    def test_price_bridge_hand_and_availability(self):
        def series(name,prices,currency='EUR'):
            return [Datum(name,TIME+timedelta(days=i),p,currency,'adjusted_close','EUR_per_share',TIME+timedelta(days=3),TIME+timedelta(days=3)) for i,p in enumerate(prices)]
        data={'A':series('A',[100,110]),'B':series('B',[100,90])}
        result=returns_from_prices(universe(),data,series('safe',[100,101]))
        np.testing.assert_allclose(result[0].excess_returns,[.09,-.11])
        self.assertEqual(result[0].available_at,TIME+timedelta(days=3))
        with self.assertRaises(ValueError): returns_from_prices(universe(),{**data,'A':series('A',[100,110],'USD')},series('safe',[100,101]))
        with self.assertRaises(ValueError): returns_from_prices(universe(),{**data,'A':series('A',[100,110,120])},series('safe',[100,101]))


class RebalanceTests(unittest.TestCase):
    def test_contribution_closes_drift_without_sales(self):
        config=replace(CFG,protected_fraction=0,equity_share=1)
        account=Account((600,400),0,1000,1000)
        updated,plan,audit=schedule(account,(.5,.5),TIME,None,'allocation',config,contribution=200)
        self.assertEqual(updated.portfolio_value,1200)
        self.assertEqual(audit['contribution'],200)
        result,fill=execute(updated,plan,TIME+timedelta(days=1),config)
        np.testing.assert_allclose(fill['trades'],[0,200],atol=1e-9)
        np.testing.assert_allclose(result.equity_values,[600,600])
        self.assertAlmostEqual(result.safe_value,0)

    def test_costs_hand_and_post_cost_budget(self):
        config=replace(CFG,commission_bps=100,half_spread_bps=100,slippage_bps=100)
        account=Account((0,0),1000,1000,1000)
        account,plan,_=schedule(account,(.5,.5),TIME,None,'allocation',config)
        result,fill=execute(account,plan,TIME+timedelta(days=1),config)
        # E=2.25*(1000-.03*E-800), E=450/1.0675.
        expected=450/1.0675
        self.assertAlmostEqual(sum(result.equity_values),expected)
        self.assertAlmostEqual(fill['costs'],.03*expected)
        self.assertAlmostEqual(result.portfolio_value+fill['costs'],1000)
        self.assertLessEqual(sum(result.equity_values),fill['risk_cap_after_costs']+1e-8)

    def test_monthly_band_and_emergency(self):
        config=replace(CFG,protected_fraction=0,equity_share=1)
        account=Account((500,500),0,1000,1000)
        _,plan,audit=schedule(account,(.5,.5),TIME,None,'allocation',config)
        self.assertIsNone(plan); self.assertEqual(audit['status'],'inside_band')
        _,plan,_=schedule(account,(.6,.4),TIME+timedelta(days=1),TIME,'allocation',config)
        self.assertIsNone(plan)
        _,plan,_=schedule(account,(.5,.5),TIME+timedelta(days=1),TIME,'risk',config,emergency=True)
        result,fill=execute(account,plan,TIME+timedelta(days=2),config)
        self.assertEqual(result.equity_values,(0,0)); self.assertEqual(result.safe_value,1000)

    def test_gap_blocks_stale_risk_target(self):
        account=Account((200,200),600,1000,1000)
        _,plan,_=schedule(account,(.6,.4),TIME,None,'allocation',CFG)
        gapped=account.mark((-.8,-.8))
        result,fill=execute(gapped,plan,TIME+timedelta(days=1),CFG)
        self.assertEqual(result.equity_values,(0,0))
        self.assertAlmostEqual(result.portfolio_value,680)

    def test_delayed_execution_staleness_and_cap(self):
        account=Account((0,0),1000,1000,1000)
        _,plan,_=schedule(account,(.5,.5),TIME,None,'allocation',CFG)
        for timestamp in (TIME,TIME+timedelta(days=8)):
            with self.assertRaises(ValueError): execute(account,plan,timestamp,CFG)
        with self.assertRaises(ValueError): schedule(account,(1,0),TIME,None,'bad',CFG)
        with self.assertRaises(ValueError): schedule(account,(.5,.5),TIME+timedelta(days=1),TIME,'bad',CFG,contribution=100)

    def test_account_mark_and_cash_return(self):
        marked=Account((200,300),500,1000,1000).mark((.1,-.1),.02)
        np.testing.assert_allclose(marked.equity_values,[220,270])
        self.assertEqual(marked.safe_value,510)
        self.assertEqual(marked.portfolio_value,1000)


class EquityAcceptanceTests(unittest.TestCase):
    def test_official_ledoit_wolf_example(self):
        # scikit-learn primary API example reports 0.23, rounded to two decimals.
        data=np.random.RandomState(0).multivariate_normal([0,0],[[.4,.2],[.2,.8]],size=50)
        self.assertAlmostEqual(estimate_covariance(data,periods_per_year=1).shrinkage,.23,places=2)

    def test_saved_bundle_replay_and_tamper(self):
        import tempfile
        from portfolio_equity.report import bundle,encoded,replay,synthetic_request
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'run.json'
            document=bundle(synthetic_request(),EquityConfig())
            file.write_bytes(encoded(document))
            self.assertEqual(replay(file)['status'],'verified')
            document['payload']['result']['allocation']['optimizer']['weights'][0]+=.01
            file.write_bytes(encoded(document))
            with self.assertRaisesRegex(ValueError,'checksum'): replay(file)

    def test_monthly_sequence_conserves_money(self):
        from portfolio_equity.report import monthly_example
        config=EquityConfig()
        result=monthly_example(config)
        self.assertEqual(len(result['entries']),3)
        costs=sum(e['result']['execution'].get('costs',0) for e in result['entries'])
        contributions=sum(e['request']['contribution'] for e in result['entries'])
        final=Account(**result['final_account'])
        self.assertEqual(contributions,200)
        self.assertAlmostEqual(final.portfolio_value+costs,10000+contributions)
        for entry in result['entries']:
            execution=entry['result']['execution']
            if 'post_account' in execution:
                self.assertLessEqual(sum(execution['post_account']['equity_values']),execution['risk_cap_after_costs']+1e-7)

    def test_execution_suffix_cannot_change_allocation(self):
        from portfolio_equity.report import run_request,synthetic_request
        a=synthetic_request()
        b={**a,'execution':{**a['execution'],'equity_returns':[-.8,-.9]}}
        self.assertEqual(run_request(a,EquityConfig())['allocation'],run_request(b,EquityConfig())['allocation'])

    def test_date_gaps_and_duplicate_returns(self):
        history=rows()
        with self.assertRaises(ValueError): allocate(universe(),history+(history[-1],),(),history[-1].observation_time,CFG)
        gap=replace(history[-1],observation_time=TIME+timedelta(days=20),available_at=TIME+timedelta(days=20))
        with self.assertRaises(ValueError): allocate(universe(),history[:2]+(gap,),(),gap.observation_time,CFG)
        intraday=replace(history[1],observation_time=TIME+timedelta(hours=1),available_at=TIME+timedelta(hours=1))
        with self.assertRaises(ValueError): allocate(universe(),(history[0],intraday),(),intraday.observation_time,CFG)

    def test_asset_permutation_equivariance(self):
        covariance=np.array([[.04,.01],[.01,.09]])
        prior=equilibrium(covariance,[.6,.4],2.5)
        a=posterior(covariance,prior,.05,[[1,-1]],[.02],[[.003]])
        b=posterior(covariance[::-1,::-1],prior[::-1],.05,[[-1,1]],[.02],[[.003]])
        np.testing.assert_allclose(a.mean,b.mean[::-1])

    def test_high_costs_and_no_implicit_leverage(self):
        account=Account((0,0),1000,1000,1000)
        costs=[]
        for bps in (0,100):
            config=replace(CFG,commission_bps=bps)
            updated,plan,_=schedule(account,(.5,.5),TIME,None,'fixture',config)
            result,audit=execute(updated,plan,TIME+timedelta(days=1),config)
            costs.append(audit['costs'])
            self.assertGreaterEqual(result.safe_value,0)
            self.assertAlmostEqual(result.portfolio_value+audit['costs'],1000)
        self.assertEqual(costs[0],0); self.assertGreater(costs[1],4)
