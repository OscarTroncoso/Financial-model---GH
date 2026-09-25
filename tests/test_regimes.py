"""Phase 8 hand calculations, independent HMM enumeration and causal audits."""
from dataclasses import asdict,replace
from datetime import timedelta
from itertools import product
from pathlib import Path
import json,math,tempfile,unittest
import numpy as np
from portfolio_fx.report import fixture
from portfolio_fx.data import NotReady
from portfolio_regimes.contracts import RegimeConfig
from portfolio_regimes.hmm import forward,expectation,emissions,fit,filter_returns
from portfolio_regimes.engine import rule,infer
from portfolio_regimes.performance import attribute
from portfolio_regimes.workflow import bundle,replay
from portfolio_regimes.audit import encoded


class FormulaTests(unittest.TestCase):
    def test_rule_hand_calculation(self):
        r=rule([.01,-.01,.01,-.01],RegimeConfig(rule_window=4))
        self.assertAlmostEqual(r['sigma'],math.sqrt(.0004/3)); self.assertEqual(r['efficiency'],0)
        self.assertEqual(r['state'],'sideways_high'); self.assertEqual(sum(r['probabilities'].values()),1)
        self.assertFalse(r['mean_reversion_confirmed'])

    def test_rule_direction_and_zero_path(self):
        cfg=RegimeConfig(rule_window=2)
        self.assertEqual(rule([.001,.001],cfg)['state'],'up_low')
        self.assertEqual(rule([-.001,-.001],cfg)['state'],'down_low')
        self.assertEqual(rule([0.,0.],cfg)['state'],'sideways_low')

    def test_forward_by_hand(self):
        f,ll=forward(np.log([[.5,.25],[.25,.5]]),[[.7,.3],[.2,.8]],[.6,.4])
        np.testing.assert_allclose(np.exp(f),[[.75,.25],[23/57,34/57]])
        self.assertAlmostEqual(math.exp(ll),.1425)

    def test_gaussian_density_by_hand(self):
        self.assertAlmostEqual(float(emissions([0.],[0.],[4.])[0,0]),-.5*math.log(8*math.pi))

    def test_training_expectation_against_all_paths(self):
        e=np.array([[.4,.7],[.8,.2],[.3,.6]]); a=np.array([[.7,.3],[.2,.8]]); pi=np.array([.6,.4])
        paths=list(product(range(2),repeat=3)); weights=[]
        for path in paths:
            weights.append(pi[path[0]]*e[0,path[0]]*a[path[0],path[1]]*e[1,path[1]]*a[path[1],path[2]]*e[2,path[2]])
        total=sum(weights); gamma=np.zeros((3,2)); counts=np.zeros((2,2))
        for path,w in zip(paths,weights):
            for t,state in enumerate(path): gamma[t,state]+=w/total
            for i,j in zip(path,path[1:]): counts[i,j]+=w/total
        g,c,ll,_=expectation(np.log(e),a,pi)
        np.testing.assert_allclose(g,gamma); np.testing.assert_allclose(c,counts)
        self.assertAlmostEqual(math.exp(ll),total)

    def test_forward_prefix_not_smoothed(self):
        e=np.log([[.5,.25],[.25,.5],[.001,.999]])
        short,_=forward(e[:2],[[.7,.3],[.2,.8]],[.6,.4])
        long,_=forward(e,[[.7,.3],[.2,.8]],[.6,.4])
        np.testing.assert_array_equal(short,long[:2])

    def test_log_filter_underflow_and_zero_transition(self):
        f,ll=forward(np.full((200,2),-10000.),[[1.,0.],[0.,1.]],[.6,.4])
        self.assertTrue(np.isfinite(ll)); np.testing.assert_allclose(np.exp(f[-1]),[.6,.4])

    def test_invalid_models(self):
        for a,pi in [([[.7,.4],[.2,.8]],[.6,.4]),([[.7,.3],[.2,.8]],[-.1,1.1])]:
            with self.assertRaises(ValueError): forward([[0.,0.]],a,pi)
        with self.assertRaises(ValueError): emissions([0.],[0.],[0.])

    def test_config_validation(self):
        for kwargs in ({'states':4},{'rule_window':True},{'low_volatility':.1},{'tolerance':float('nan')},{'training_window':10}):
            with self.assertRaises(ValueError): RegimeConfig(**kwargs)


class CausalityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows,_=fixture(); cls.cutoff=cls.rows[12*48].start; cls.time=cls.rows[13*48-1].end

    def test_fit_and_state_order(self):
        r=infer(self.rows,self.time,self.cutoff)['payload']['hmm']; self.assertEqual(r['status'],'READY')
        model=r['fit']; self.assertTrue(model['converged'])
        self.assertEqual(sorted(model['variances']),model['variances'])
        self.assertTrue(all(b>=a-1e-7 for a,b in zip(model['log_likelihood_history'],model['log_likelihood_history'][1:])))
        self.assertAlmostEqual(sum(r['probabilities'].values()),1)
        self.assertTrue(all(b['available_at']<=self.cutoff.isoformat() for b in r['inputs']['training_bars']))

    def test_future_candles_cannot_change_inference(self):
        expected=infer(self.rows,self.time,self.cutoff)
        changed=tuple(replace(r,open=r.open*3,high=r.high*3,low=r.low*3,close=r.close*3) if r.end>self.time else r for r in self.rows)
        self.assertEqual(infer(changed,self.time,self.cutoff),expected)
        self.assertEqual(infer(tuple(r for r in self.rows if r.available_at<=self.time),self.time,self.cutoff),expected)

    def test_training_vintage_frozen_after_cutoff(self):
        original=self.rows[12*48-1]
        corrected=replace(original,open=original.open*1.01,high=original.high*1.01,low=original.low*1.01,close=original.close*1.01,
                          ingested_at=self.cutoff+timedelta(minutes=30),available_at=self.cutoff+timedelta(minutes=30))
        expected=infer(self.rows,self.time,self.cutoff)['payload']['hmm']
        self.assertEqual(infer(self.rows+(corrected,),self.time,self.cutoff)['payload']['hmm'],expected)

    def test_late_future_revision_excluded(self):
        old=self.rows[13*48-1]
        correction=replace(old,open=old.open*2,high=old.high*2,low=old.low*2,close=old.close*2,
                           ingested_at=self.time+timedelta(days=1),available_at=self.time+timedelta(days=1))
        self.assertEqual(infer(self.rows+(correction,),self.time,self.cutoff),infer(self.rows,self.time,self.cutoff))

    def test_later_observation_does_not_refit_hmm(self):
        first=infer(self.rows,self.time,self.cutoff)['payload']['hmm']
        later=infer(self.rows,self.time+timedelta(hours=4),self.cutoff)['payload']['hmm']
        self.assertEqual(first['fit'],later['fit'])
        self.assertEqual(first['filtered_path'],later['filtered_path'][:len(first['filtered_path'])])

    def test_stale_and_missing_abstain(self):
        r=infer(self.rows[:13*48],self.time+timedelta(days=5),self.cutoff)['payload']
        self.assertTrue(all(r[m]['status']=='UNKNOWN' for m in ('rule','hmm')))
        empty=infer((),self.time,self.cutoff)['payload']
        self.assertEqual(empty['hmm']['probabilities'],{'UNKNOWN':1.})

    def test_gap_abstains(self):
        rows=tuple(r for r in self.rows if not self.cutoff<r.end<self.cutoff+timedelta(hours=20))
        cfg=RegimeConfig(maximum_gap_hours=1)
        r=infer(rows,self.time,self.cutoff,cfg)['payload']
        self.assertEqual(r['hmm']['reason'],'excessive_history_gap')

    def test_nonconverged_fit_abstains(self):
        r=infer(self.rows,self.time,self.cutoff,RegimeConfig(max_iterations=2))['payload']
        self.assertEqual(r['rule']['status'],'READY'); self.assertEqual(r['hmm']['reason'],'hmm_not_converged')

    def test_weekend_training_cutoff_uses_last_closed_bar(self):
        monday=self.rows[20*48].start
        prior_close=self.rows[20*48-1].end
        self.assertGreater((monday-prior_close).total_seconds(),24*3600)
        r=infer(self.rows,monday+timedelta(hours=4),prior_close)['payload']
        self.assertEqual(r['hmm']['status'],'READY')
        self.assertEqual(r['hmm']['inputs']['training_bars'][-1]['end'],prior_close.isoformat())

    def test_invalid_cutoff_rejected(self):
        for cutoff in (self.time,self.time+timedelta(hours=4),self.cutoff+timedelta(minutes=30)):
            with self.assertRaises(ValueError): infer(self.rows,self.time,cutoff)

    def test_degenerate_training(self):
        with self.assertRaises(NotReady): fit([0.]*60)

    def test_scaling_uses_only_training(self):
        x=[.001*math.sin(i*.3)+.0002*math.cos(i) for i in range(60)]
        m=fit(x); n=fit([3*r+.01 for r in x])
        p,_=filter_returns([.001,-.001],m); q,_=filter_returns([.013,.007],n)
        np.testing.assert_allclose(p,q,atol=1e-9)

    def test_bundle_exact_replay_and_tamper(self):
        req=dict(candles=[asdict(r) for r in self.rows[:13*48]],times=[self.time],training_cutoff=self.cutoff,config=asdict(RegimeConfig()))
        doc=bundle(req)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'run.json'; p.write_bytes(encoded(doc)); self.assertEqual(replay(p)['status'],'verified')
            doc['payload']['records'][0]['payload']['rule']['state']='fake'; p.write_bytes(encoded(doc))
            with self.assertRaises(ValueError): replay(p)


class AttributionTests(unittest.TestCase):
    def test_net_cost_carry_safe_income_and_reversal_lineage(self):
        def stamp(hour): return f'2020-01-06T{hour:02d}:00:00+00:00'
        def fill(hour,units,signal): return dict(time=stamp(hour),quantity_eur=units,signal_id=signal)
        def trade(hour,direction,net,cost,carry):
            return dict(entry_time=stamp(hour),direction=direction,units_eur=10.,net_pnl=net,costs=cost,carry=carry,gross_pnl=net+cost-carry,holding_hours=1.)
        result=dict(signals=[dict(plan_id='a',payload=dict(decision_time=stamp(0))),dict(plan_id='b',payload=dict(decision_time=stamp(4)))],
                    fills=[fill(1,10,'a'),fill(5,-10,'b'),fill(5,-10,'b'),fill(6,10,None)],
                    trades=[trade(1,1,8.,3.,1.),trade(5,-1,-4.,2.,-1.)],totals=dict(safe_income=2.),initial_nav=100.,final_nav=106.)
        records=[dict(regime_id=str(h),payload=dict(decision_time=stamp(h),rule=dict(state=s,probabilities={s:1.}))) for h,s in ((0,'up_low'),(4,'UNKNOWN'))]
        r=attribute(result,records,'rule')
        self.assertEqual(r['trade_net_pnl_usd'],4.); self.assertEqual(r['unallocated_safe_income_usd'],2.)
        self.assertEqual(r['groups']['up_low']['expectancy_usd'],8.); self.assertEqual(r['groups']['UNKNOWN']['hit_rate'],0.)
        self.assertEqual(r['assignments'][1]['decision_time'],stamp(4))
        with self.assertRaises(ValueError): attribute(result,records[:1],'rule')

if __name__=='__main__': unittest.main()
