"""Phase-7 hand calculations, capacity limits, causal fits and protective fills."""
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
import math
import unittest
from unittest.mock import patch
from portfolio_fx.contracts import Candle,ExecutionConfig,FXConfig
from portfolio_fx.data import NotReady
from portfolio_fx.report import fixture
from portfolio_fx_risk.contracts import RiskConfig,VolatilityConfig,Capacity
from portfolio_fx_risk.volatility import ewma_step,garch_step,estimate,forecast
from portfolio_fx_risk.sizing import size,stop_distance
from portfolio_fx_risk.plans import propose
from portfolio_fx_risk.engine import run,barrier

T=datetime(2020,1,6,tzinfo=timezone.utc)
ZERO=ExecutionConfig(commission_bps=0,half_spread_bps=0,slippage_bps=0,safe_annual_rate=0,long_carry_annual_rate=0,short_carry_annual_rate=0)

def candle(i,price=1.):
    start=T+timedelta(minutes=30*i); end=start+timedelta(minutes=30)
    return Candle(start,end,price,price,price,price,end,end,'risk hand case','EURUSD','mid')

def manual(direction=1,distance=.01):
    def build(rows,rates,time,model,capacity,risk,volatility,features,execution):
        sizing=size(1.,direction,distance,capacity,risk,execution)
        return dict(plan_id='hand-plan',payload=dict(decision_time=time.isoformat(),sizing=sizing))
    return build

class VolatilityTests(unittest.TestCase):
    def test_realized_by_hand(self):
        value=estimate((.01,-.01,.01,-.01),VolatilityConfig(window=4,seed_window=2))
        self.assertAlmostEqual(value['variance'],.0004/3)
        self.assertAlmostEqual(value['sigma'],math.sqrt(.0004/3))

    def test_ewma_recursion(self):
        self.assertAlmostEqual(ewma_step(.0001,.02,.94),.000118)
        value=estimate((.01,-.01,.02,-.02),VolatilityConfig(model='ewma',window=4,seed_window=2,ewma_decay=.5))
        self.assertAlmostEqual(value['variance'],.000325)

    def test_garch_recursion_and_constraints(self):
        self.assertAlmostEqual(garch_step(.0001,.02,.000001,.1,.8),.000121)
        for a,b in ((-.1,.8),(.2,.8),(.2,.9)):
            with self.assertRaises(ValueError): garch_step(.0001,.02,.000001,a,b)

    def test_garch_targeting_and_likelihood_hand(self):
        cfg=VolatilityConfig(model='garch',window=4,seed_window=2,garch_alpha_grid=(.1,),garch_beta_grid=(.8,))
        result=estimate((.01,-.01,.02,-.02),cfg)
        self.assertAlmostEqual(result['parameters']['omega'],.000025)
        self.assertAlmostEqual(result['variance'],.000181)
        expected=(math.log(.0001)+4+math.log(.000145)+.0004/.000145)/2
        self.assertAlmostEqual(result['parameters']['score'],expected)

    def test_grid_fit_selects_best_valid_candidate(self):
        cfg=VolatilityConfig(model='garch',window=8,seed_window=2)
        value=estimate((.01,-.01,.02,-.02,.005,-.005,.003,-.003),cfg)
        self.assertEqual(value['parameters']['score'],min(r['score'] for r in value['candidates']))
        self.assertTrue(all(r['alpha']+r['beta']<1 and r['omega']>0 for r in value['candidates']))

    def test_degenerate_nonfinite_and_invalid_settings(self):
        with self.assertRaises(NotReady): estimate((0.,)*4,VolatilityConfig(window=4,seed_window=2))
        with self.assertRaises(ValueError): estimate((float('nan'),)*4,VolatilityConfig(window=4,seed_window=2))
        with self.assertRaises(ValueError): VolatilityConfig(model='invented')
        with self.assertRaises(ValueError): VolatilityConfig(garch_alpha_grid=(.5,),garch_beta_grid=(.5,))
        with self.assertRaises(ValueError): VolatilityConfig(window=12,seed_window=12)

    def test_forecast_future_invariance_and_clock(self):
        rows,_=fixture(); time=rows[767].end
        for model in ('realized','ewma','garch'):
            cfg=VolatilityConfig(model=model)
            full=forecast(rows,time,cfg); prefix=forecast(rows[:768],time,cfg)
            self.assertEqual(full,prefix)
            self.assertTrue(all(r['available_at']<=time for r in full['market_inputs']))
        with self.assertRaises(NotReady): forecast(rows[:48],rows[47].end,VolatilityConfig())
        with self.assertRaises(NotReady): forecast(rows,rows[-1].end+timedelta(days=2),VolatilityConfig())

class SizingTests(unittest.TestCase):
    def roomy(self,**kw):
        return RiskConfig(maximum_portfolio_notional=1,maximum_notional_usd=1e6,maximum_units=1e6,unit_step=1,minimum_units=1,**kw)

    def test_volatility_stop_and_floor(self):
        cfg=RiskConfig()
        self.assertAlmostEqual(stop_distance(1.2,.005,cfg),.012)
        self.assertAlmostEqual(stop_distance(1.2,.000001,cfg),.0005)
        self.assertAlmostEqual(stop_distance(1.2,.005,replace(cfg,stop_horizon_bars=4)),.024)
        with self.assertRaises(NotReady): stop_distance(1.2,.2,cfg)

    def test_stop_risk_relationship_long_short_and_pips(self):
        for direction in (1,-1):
            value=size(1.,direction,.01,Capacity(10000,1000),self.roomy(),ZERO)
            self.assertEqual(value['units_eur'],1000); self.assertEqual(value['modeled_stop_loss_usd'],10)
            self.assertEqual(value['stop_pips'],100); self.assertEqual(value['pip_value_usd'],.1)
            self.assertAlmostEqual(value['stop'],1-direction*.01)
            self.assertAlmostEqual(value['take_profit'],1+direction*.02)
        self.assertEqual(size(1.,1,.02,Capacity(10000,1000),self.roomy(),ZERO)['units_eur'],500)

    def test_cost_and_carry_reserve_hand(self):
        cfg=self.roomy(); costs=replace(ZERO,commission_bps=10,long_carry_annual_rate=-.365)
        value=size(1.,1,.01,Capacity(10000,1000),cfg,costs)
        loss=.01+.001*(1+1.02)+1.02*.365*48/(365*24)
        self.assertEqual(value['units_eur'],math.floor(10/loss))
        self.assertAlmostEqual(value['modeled_stop_loss_usd'],value['units_eur']*loss)
        self.assertLessEqual(value['modeled_stop_loss_usd'],10)

    def test_rounding_down_and_minimum(self):
        cfg=replace(self.roomy(),unit_step=100,minimum_units=100)
        value=size(1.,1,.011,Capacity(10000,1000),cfg,ZERO)
        self.assertEqual(value['units_eur'],900)
        self.assertEqual(size(1.,1,.011,Capacity(10000,10),cfg,ZERO)['state'],'NO_TRADE')

    def test_hard_controls(self):
        for cfg,cap in ((RiskConfig(kill_switch=True),Capacity(10000,1000)),(RiskConfig(),Capacity(10000,1000,open_positions=1)),
                        (RiskConfig(),Capacity(10000,1000,open_risk_usd=200)),(RiskConfig(),Capacity(10000,1000,margin_used_usd=1000))):
            self.assertEqual(size(1.,1,.01,cap,cfg,ZERO)['state'],'NO_TRADE')
        with self.assertRaises(ValueError): RiskConfig(risk_per_trade=.1)
        with self.assertRaises(ValueError): Capacity(100,101)
        with self.assertRaises(ValueError): RiskConfig(maximum_holding_hours=.3)

    def test_post_cost_portfolio_risk_limit(self):
        cfg=self.roomy(maximum_portfolio_risk=.0005)
        costs=replace(ZERO,commission_bps=100)
        cap=Capacity(10000,1000)
        value=size(1.,1,.01,cap,cfg,costs)
        post_nav=10000-value['units_eur']*.01
        self.assertLessEqual(value['modeled_stop_loss_usd'],post_nav*.0005)

    def test_notional_and_margin_caps_include_entry_cost(self):
        cfg=RiskConfig(unit_step=1,minimum_units=1)
        costs=replace(ZERO,commission_bps=100)
        value=size(1.,1,.0005,Capacity(10000,1000),cfg,costs)
        post_nav=10000-value['units_eur']*.01
        self.assertLessEqual(value['notional_usd'],post_nav*.1)
        self.assertLessEqual(value['margin_usd']+value['units_eur']*.01,1000)
        cap=replace(cfg,maximum_notional_usd=300)
        self.assertLessEqual(size(1.,1,.0005,Capacity(10000,1000),cap,ZERO)['notional_usd'],300)

class RiskExecutionTests(unittest.TestCase):
    def evaluate(self,rows,direction=1,risk=None,execution=ZERO):
        cfg=risk or RiskConfig(minimum_units=1,unit_step=1,maximum_portfolio_notional=1)
        with patch('portfolio_fx_risk.engine.propose',side_effect=manual(direction)):
            return run(tuple(rows),(),'trend',rows[0].start,rows[-1].end,execution=execution,risk=cfg)

    def test_barrier_gap_and_ambiguous_priority(self):
        row=replace(candle(0),open=1.,high=1.03,low=.98)
        self.assertEqual(barrier({'stop':.99,'take_profit':1.02},1,row,False),(.99,'stop'))
        self.assertEqual(barrier({'stop':1.01,'take_profit':.98},-1,row,False),(1.01,'stop'))
        gap=replace(candle(0,.97),high=.98,low=.96)
        self.assertEqual(barrier({'stop':.99,'take_profit':1.02},1,gap,True),(.97,'gap_stop'))
        self.assertEqual(barrier({'stop':1.01,'take_profit':.98},-1,gap,True),(.98,'gap_take_profit'))

    def test_long_short_stop_loss_budget(self):
        for direction in (1,-1):
            rows=[candle(i) for i in range(11)]
            rows[-1]=replace(rows[-1],low=.98 if direction==1 else 1.,high=1.02 if direction==-1 else 1.)
            value=self.evaluate(rows,direction)
            self.assertEqual(value['trades'][0]['exit_reason'],'stop')
            self.assertAlmostEqual(value['trades'][0]['net_pnl'],-10)
            self.assertFalse(value['trades'][0]['budget_exceeded'])
            self.assertAlmostEqual(value['final_nav'],9990)

    def test_take_profit_and_time_stop(self):
        rows=[candle(i) for i in range(14)]
        rows[10]=replace(rows[10],high=1.03)
        value=self.evaluate(rows); self.assertEqual(value['trades'][0]['exit_reason'],'take_profit')
        self.assertAlmostEqual(value['trades'][0]['net_pnl'],20)
        cfg=RiskConfig(minimum_units=1,unit_step=1,maximum_portfolio_notional=1,maximum_holding_hours=1)
        value=self.evaluate([candle(i) for i in range(14)],risk=cfg)
        self.assertEqual(value['trades'][0]['exit_reason'],'time_stop')
        self.assertEqual(value['trades'][0]['holding_hours'],1)

    def test_gap_can_exceed_budget_without_reentry(self):
        rows=[candle(i) for i in range(12)]; rows[10]=candle(10,.97); rows[11]=candle(11,.97)
        value=self.evaluate(rows)
        trade=value['trades'][0]
        self.assertEqual(trade['exit_reason'],'gap_stop'); self.assertAlmostEqual(trade['net_pnl'],-30)
        self.assertTrue(trade['budget_exceeded']); self.assertEqual(len(value['trades']),1)

    def test_gap_take_profit_has_no_price_improvement(self):
        rows=[candle(i) for i in range(12)]
        rows[10]=candle(10,1.03); rows[11]=candle(11,1.03)
        result=self.evaluate(rows)
        self.assertEqual(result['trades'][0]['exit_reason'],'gap_take_profit')
        self.assertAlmostEqual(result['trades'][0]['net_pnl'],20)
        self.assertAlmostEqual(result['final_nav'],10020)

    def test_short_take_profit_and_gap_stop(self):
        rows=[candle(i) for i in range(12)]
        rows[10]=replace(rows[10],low=.97)
        value=self.evaluate(rows,-1)
        self.assertAlmostEqual(value['trades'][0]['net_pnl'],20)
        rows[10]=candle(10,1.03); rows[11]=candle(11,1.03)
        value=self.evaluate(rows,-1)
        self.assertEqual(value['trades'][0]['exit_reason'],'gap_stop')
        self.assertAlmostEqual(value['trades'][0]['net_pnl'],-30)
        self.assertTrue(value['trades'][0]['budget_exceeded'])

    def test_entry_drift_rejects_stale_price(self):
        rows=[candle(i) for i in range(11)]; rows[9]=candle(9,1.02); rows[10]=candle(10,1.02)
        self.assertFalse(self.evaluate(rows)['trades'])

    def test_stop_with_costs_and_carry_stays_within_budget(self):
        rows=[candle(i) for i in range(11)]; rows[-1]=replace(rows[-1],low=.98)
        settings=replace(ZERO,commission_bps=1,half_spread_bps=1,slippage_bps=1,long_carry_annual_rate=-.05)
        value=self.evaluate(rows,execution=settings); trade=value['trades'][0]
        self.assertLessEqual(-trade['net_pnl'],trade['modeled_stop_loss_usd'])
        self.assertLessEqual(trade['modeled_stop_loss_usd'],trade['risk_budget_usd'])
        self.assertAlmostEqual(value['final_nav']-10000,sum(t['net_pnl'] for t in value['trades']))

    def test_causal_plan_and_no_trade_paths(self):
        rows,rates=fixture(); time=rows[767].end; capacity=Capacity(10000,1000)
        for model in ('realized','ewma','garch'):
            cfg=VolatilityConfig(model=model)
            full=propose(rows,rates,time,'trend',capacity,volatility=cfg)
            prefix=propose(rows[:768],tuple(r for r in rates if r.available_at<=time),time,'trend',capacity,volatility=cfg)
            self.assertEqual(full,prefix); self.assertFalse(full['payload']['executable'])
        self.assertEqual(propose(rows[:48],(),rows[47].end,'trend',capacity)['payload']['sizing']['state'],'NO_TRADE')

    def test_engine_prefix_invariance_and_risk_reconciliation(self):
        rows,rates=fixture(); start=rows[12*48].start; end=rows[14*48-1].end
        full=run(rows,rates,'trend',start,end)
        prefix=run(rows[:14*48],rates,'trend',start,end)
        self.assertEqual(full,prefix)
        self.assertTrue(full['trades'])
        self.assertTrue(all(t['modeled_stop_loss_usd']<=t['risk_budget_usd']+1e-8 for t in full['trades']))

class RiskWorkflowTests(unittest.TestCase):
    def test_backtest_and_proposal_replay_tamper(self):
        import json,tempfile
        from pathlib import Path
        from portfolio_fx_risk.workflow import bundle,replay
        from portfolio_fx_risk.audit import encoded
        rows,rates=fixture()
        request=dict(candles=[asdict(r) for r in rows],rates=[asdict(r) for r in rates],model='trend',
            start=rows[12*48].start,end=rows[13*48-1].end,config=asdict(FXConfig()),execution=asdict(ZERO),
            risk=asdict(RiskConfig()),volatility=asdict(VolatilityConfig()),fx_capital_fraction=.1)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'run.json'; saved=bundle(request); path.write_bytes(encoded(saved))
            self.assertEqual(replay(path)['status'],'verified')
            saved['payload']['result']['final_nav']+=1; path.write_bytes(encoded(saved))
            with self.assertRaises(ValueError): replay(path)
            for key in ('start','end','fx_capital_fraction'): request.pop(key)
            request.update(time=rows[13*48-1].end,capacity=asdict(Capacity(10000,1000)))
            saved=bundle(request,'proposal'); path.write_bytes(encoded(saved))
            self.assertEqual(replay(path)['status'],'verified')

if __name__=='__main__': unittest.main()
