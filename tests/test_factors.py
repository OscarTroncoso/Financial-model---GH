"""Phase 5: hand statistics, availability, revisions, purging and BL integration."""
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from portfolio_data.contracts import Datum
from portfolio_equity.contracts import Universe
from portfolio_factors.core import Feature,FactorSpec,FactorConfig,normalize,snapshot,encoded
from portfolio_factors.prices import PriceFactorConfig,price_features,select_vintages
from portfolio_factors.learning import LearningConfig,ols,label_sample,generate_view,validate_snapshot
from portfolio_factors.workflow import compute,bundle,replay
from portfolio_factors.report import synthetic_data

T=datetime(2020,1,1,16,tzinfo=timezone.utc)
U=Universe(('A','B','C'),'EUR',(.4,.35,.25),T,'synthetic universe')
F=FactorConfig((FactorSpec('factor','ratio',1,1,30),))
L=LearningConfig('A','B',horizon_sessions=1,periods_per_year=1,minimum_training=3,
                 maximum_training=10,embargo_days=0,max_abs_annual_view=1)


def feature(asset,value,time=T,factor='factor',unit='ratio'):
    return Feature(asset,factor,value,unit,time,time,time,time,'synthetic','v1')


def scores(time,values):
    return snapshot(U,tuple(feature(a,v,time) for a,v in zip(U.asset_ids,values)),time,F)


def price(asset,time,value=100,available=None):
    available=available or time
    return Datum(asset,time,value,'EUR','adjusted_close','EUR_per_share',available,available)


def sample(index,values,realized=.01):
    time=T+timedelta(days=index*3)
    point=scores(time,values)
    paths={'A':[price('A',time),price('A',time+timedelta(days=1),100*(1+realized))],
           'B':[price('B',time),price('B',time+timedelta(days=1))]}
    return label_sample(point,paths,L)


def training():
    return (sample(0,(1,2,4),-.01),sample(1,(3,1,4),.02),sample(2,(2,1,4),.012))


class FactorSnapshotTests(unittest.TestCase):
    def test_zscore_hand(self):
        result=normalize((1,2,3),1,3)
        self.assertEqual(result['mean'],2)
        self.assertAlmostEqual(result['population_std'],np.sqrt(2/3))
        np.testing.assert_allclose(result['scores'],[-np.sqrt(1.5),0,np.sqrt(1.5)])

    def test_direction_clipping_and_constant(self):
        np.testing.assert_allclose(normalize((1,2,3),-1,1)['scores'],[1,0,-1])
        self.assertEqual(normalize((2,2),1,3)['scores'],[0,0])
        self.assertEqual(normalize((2,2),1,3)['status'],'constant')
        with self.assertRaises(ValueError): normalize((float('nan'),1),1,3)
        with self.assertRaises(ValueError): normalize((1e308,1e308),1,3)

    def test_weighted_composite_hand(self):
        cfg=FactorConfig((FactorSpec('quality','ratio',1,.75,30),FactorSpec('risk','ratio',-1,.25,30)))
        u=Universe(('A','B'),'EUR',(.5,.5),T,'fixture')
        features=tuple(feature(a,v,factor=f) for f in ('quality','risk') for a,v in (('A',1),('B',3)))
        result=snapshot(u,features,T,cfg)['payload']
        self.assertEqual(result['composite_scores'],{'A':-.5,'B':.5})
        self.assertEqual(len(result['selected_inputs']),4)

    def test_future_revision_cannot_rewrite_past(self):
        rows=tuple(feature(a,v) for a,v in zip(U.asset_ids,(1,2,3)))
        revision=replace(rows[0],value=100,published_at=T+timedelta(days=2),ingested_at=T+timedelta(days=2),
                         available_at=T+timedelta(days=2),revision_id='v2')
        a=snapshot(U,rows,T,F)
        self.assertEqual(a,snapshot(U,rows+(revision,),T,F))
        b=snapshot(U,rows+(revision,),T+timedelta(days=2),F)
        self.assertEqual(b['payload']['selected_inputs'][0]['value'],100)

    def test_late_revision_of_old_period_does_not_replace_newer(self):
        time=T+timedelta(days=3)
        rows=tuple(feature(a,v,time) for a,v in zip(U.asset_ids,(1,2,3)))
        old=replace(feature('A',100,T),published_at=time,ingested_at=time,available_at=time,revision_id='late')
        self.assertEqual(snapshot(U,rows,time,F),snapshot(U,rows+(old,),time,F))

    def test_conflicting_ties_and_exact_duplicates(self):
        rows=tuple(feature(a,v) for a,v in zip(U.asset_ids,(1,2,3)))
        self.assertEqual(snapshot(U,rows,T,F),snapshot(U,rows+(rows[0],),T,F))
        with self.assertRaises(ValueError): snapshot(U,rows+(replace(rows[0],value=5),),T,F)

    def test_missing_stale_units_universe_and_availability(self):
        rows=tuple(feature(a,v) for a,v in zip(U.asset_ids,(1,2,3)))
        with self.assertRaises(ValueError): snapshot(U,rows[:2],T,F)
        with self.assertRaises(ValueError): snapshot(U,rows,T+timedelta(days=31),F)
        with self.assertRaises(ValueError): snapshot(U,(replace(rows[0],unit='USD'),)+rows[1:],T,F)
        with self.assertRaises(ValueError): snapshot(replace(U,available_at=T+timedelta(days=1)),rows,T,F)
        with self.assertRaises(ValueError): replace(rows[0],published_at=T+timedelta(days=1))
        with self.assertRaises(ValueError): replace(rows[0],value=True)

    def test_configuration_validation(self):
        with self.assertRaises(ValueError): FactorConfig((FactorSpec('x','ratio',1,.5,7),))
        with self.assertRaises(ValueError): FactorConfig(F.factors,minimum_assets=1)
        with self.assertRaises(ValueError): FactorSpec('x','ratio',0,1,7)
        with self.assertRaises(ValueError): replace(L,max_confidence=1)
        with self.assertRaises(ValueError): replace(L,minimum_training=2)
        with self.assertRaises(ValueError): PriceFactorConfig(momentum_skip=252)

    def test_audit_recomputes_and_detects_score_tampering(self):
        point=scores(T,(1,2,3))
        self.assertEqual(validate_snapshot(point),point['payload'])
        bad=copy.deepcopy(point); bad['payload']['composite_scores']['A']=10
        with self.assertRaises(ValueError): validate_snapshot(bad)
        from portfolio_factors.core import digest
        bad['snapshot_id']=digest(bad['payload'])
        with self.assertRaises(ValueError): validate_snapshot(bad)


class PriceFactorsTests(unittest.TestCase):
    def test_momentum_volatility_hand(self):
        config=PriceFactorConfig(momentum_lookback=3,momentum_skip=1,volatility_window=2,periods_per_year=1)
        values=(100,110,121,108.9)
        series={a:[price(a,T+timedelta(days=i),p) for i,p in enumerate(values)] for a in U.asset_ids}
        features,audit=price_features(U,series,T+timedelta(days=3),config)
        self.assertAlmostEqual(features[0].value,.21)
        self.assertAlmostEqual(features[1].value,np.sqrt(.02))
        self.assertIn(audit['input_id'],features[0].source_id)

    def test_price_vintage_selection_before_ranking(self):
        original=price('A',T,100)
        revised=price('A',T,110,T+timedelta(days=2))
        self.assertEqual(select_vintages([original,revised],T),[original])
        self.assertEqual(select_vintages([original,revised],T+timedelta(days=2)),[revised])
        with self.assertRaises(ValueError): select_vintages([original,replace(original,value=120)],T)

    def test_download_today_not_historical_feature(self):
        config=PriceFactorConfig(momentum_lookback=3,momentum_skip=1,volatility_window=2)
        series={a:[price(a,T+timedelta(days=i),100+i,T+timedelta(days=10)) for i in range(4)] for a in U.asset_ids}
        with self.assertRaises(ValueError): price_features(U,series,T+timedelta(days=3),config)

    def test_price_session_and_currency_rejection(self):
        config=PriceFactorConfig(momentum_lookback=3,momentum_skip=1,volatility_window=2)
        series={a:[price(a,T+timedelta(days=i),100+i) for i in range(4)] for a in U.asset_ids}
        series['A']=[replace(r,currency='USD') for r in series['A']]
        with self.assertRaises(ValueError): price_features(U,series,T+timedelta(days=3),config)


class LearningTests(unittest.TestCase):
    def test_ols_hand_and_mean_uncertainty(self):
        result=ols(np.array([-1,0,1,2]),np.array([-1,1,2,4]),.5)
        self.assertAlmostEqual(result['intercept'],.7)
        self.assertAlmostEqual(result['slope'],1.6)
        self.assertAlmostEqual(result['residual_variance'],.1)
        self.assertAlmostEqual(result['prediction'],1.5)
        self.assertAlmostEqual(result['mean_variance'],.025)

    def test_label_hand_and_provenance(self):
        record=sample(0,(1,2,3),.03)
        self.assertAlmostEqual(record['payload']['period_spread_return'],.03)
        self.assertEqual(record['payload']['available_at'],(T+timedelta(days=1)).isoformat())
        self.assertEqual(record['payload']['snapshot']['payload']['decision_time'],T.isoformat())

    def test_view_and_effective_omega_match(self):
        current=scores(T+timedelta(days=10),(2,1,4))
        view,audit=generate_view(current,training(),np.eye(3)*.04,.05,L)
        self.assertIsNotNone(view)
        self.assertLessEqual(view.confidence,L.max_confidence)
        self.assertEqual(view.available_at,T+timedelta(days=10))
        from portfolio_equity.models import confidence_variance
        self.assertAlmostEqual(confidence_variance(np.eye(3)*.04,view.pick,.05,view.confidence),audit['effective_omega'])
        self.assertIn(audit['model_id'],view.source)

    def test_future_label_does_not_change_prediction(self):
        current=scores(T+timedelta(days=10),(2,1,4))
        base=generate_view(current,training(),np.eye(3)*.04,.05,L)
        future=sample(5,(4,1,2),.5)
        self.assertEqual(base,generate_view(current,training()+(future,),np.eye(3)*.04,.05,L))

    def test_insufficient_embargo_and_stale_no_view(self):
        current=scores(T+timedelta(days=10),(2,1,4))
        view,audit=generate_view(current,training()[:2],np.eye(3)*.04,.05,L)
        self.assertIsNone(view); self.assertEqual(audit['reason'],'insufficient_nonoverlapping_labels')
        view,audit=generate_view(current,training(),np.eye(3)*.04,.05,replace(L,embargo_days=5))
        self.assertIsNone(view)
        view,audit=generate_view(current,training(),np.eye(3)*.04,.05,replace(L,maximum_recent_label_age_days=1))
        self.assertIsNone(view); self.assertEqual(audit['reason'],'stale_training_labels')

    def test_overlap_is_purged(self):
        cfg=replace(L,horizon_sessions=2)
        samples=[]
        for i in range(5):
            t=T+timedelta(days=i)
            point=scores(t,(1+i,2,4))
            paths={a:[price(a,t+timedelta(days=j),100+j*(1 if a=='A' else .2)) for j in range(3)] for a in ('A','B')}
            samples.append(label_sample(point,paths,cfg))
        _,audit=generate_view(scores(T+timedelta(days=10),(3,2,4)),tuple(samples),np.eye(3)*.04,.05,cfg)
        self.assertEqual(len(audit['training_sample_ids']),3)
        chosen=[s['payload'] for s in samples if s['sample_id'] in audit['training_sample_ids']]
        for a,b in zip(chosen,chosen[1:]): self.assertLessEqual(a['end_time'],b['start_time'])

    def test_extrapolation_and_constant_scores(self):
        current=scores(T+timedelta(days=10),(100,1,4))
        view,audit=generate_view(current,training(),np.eye(3)*.04,.05,L)
        self.assertIsNone(view); self.assertEqual(audit['reason'],'score_extrapolation')
        flat=tuple(sample(i,(1,2,3),.01*i) for i in range(3))
        view,audit=generate_view(scores(T+timedelta(days=10),(1,2,3)),flat,np.eye(3)*.04,.05,L)
        self.assertIsNone(view); self.assertEqual(audit['reason'],'constant_training_scores')

    def test_labels_reject_wrong_horizon_and_past_start(self):
        point=scores(T+timedelta(days=1),(1,2,3))
        paths={a:[price(a,T),price(a,T+timedelta(days=1))] for a in ('A','B')}
        with self.assertRaises(ValueError): label_sample(point,paths,L)
        with self.assertRaises(ValueError): label_sample(scores(T,(1,2,3)),paths,replace(L,horizon_sessions=2))

    def test_conflicting_training_labels_fail(self):
        rows=training()+(sample(0,(1,2,4),.1),)
        with self.assertRaises(ValueError): generate_view(scores(T+timedelta(days=10),(2,1,4)),rows,np.eye(3)*.04,.05,L)

    def test_invalid_ols_and_forecast_risk_bound(self):
        with self.assertRaises(ValueError): ols(np.ones(3),np.arange(3),1)
        view,audit=generate_view(scores(T+timedelta(days=10),(2,1,4)),training(),np.eye(3)*.04,.05,replace(L,max_abs_annual_view=1e-8))
        self.assertIsNone(view); self.assertEqual(audit['reason'],'forecast_outside_risk_bounds')


class SystematicWorkflowTests(unittest.TestCase):
    def test_full_flow_temporal_audit_and_constraints(self):
        request,settings=synthetic_data(); result=compute(request,settings)
        self.assertIsNotNone(result['view'])
        self.assertEqual(result['view']['annual_excess_return'],result['allocation']['Q'][0])
        self.assertAlmostEqual(result['allocation']['Omega'][0][0],result['model']['effective_omega'])
        self.assertAlmostEqual(sum(result['allocation']['optimizer']['weights']),1)
        self.assertTrue(all(0<=w<=.6+1e-10 for w in result['allocation']['optimizer']['weights']))
        self.assertTrue(all(t<=result['model']['decision_time'] for t in result['model']['training_available_times']))
        sources={a['input_id'] for a in result['price_input_audits']}
        for sample in result['training_samples']:
            for record in sample['payload']['snapshot']['payload']['selected_inputs']:
                self.assertIn(record['source_id'].split(':')[1],sources)

    def test_future_price_suffix_invariance(self):
        request,settings=synthetic_data()
        original=compute(request,settings)
        cut=request['decision_time']
        shorter={**request,'prices':{a:[r for r in rows if r['observation_time']<=cut.isoformat()] for a,rows in request['prices'].items()},
                 'safe_prices':[r for r in request['safe_prices'] if r['observation_time']<=cut.isoformat()]}
        reduced=compute(shorter,settings)
        self.assertEqual(original,reduced)

    def test_bundle_replay_and_tamper(self):
        request,settings=synthetic_data()
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'view.json'; document=bundle(request,settings)
            file.write_bytes(encoded(document)); self.assertEqual(replay(file)['status'],'verified')
            document['payload']['result']['view']['confidence']=1
            file.write_bytes(encoded(document))
            with self.assertRaises(ValueError): replay(file)

    def test_phase4_baseline_when_training_missing(self):
        request,settings=synthetic_data(); request['training_times']=[]
        result=compute(request,settings)
        self.assertIsNone(result['view']); self.assertEqual(result['allocation'],result['baseline_allocation'])
