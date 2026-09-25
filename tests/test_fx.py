"""Hand accounting, temporal causality and reproducibility of phase-6 baselines."""
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import math
import tempfile
import unittest
from unittest.mock import patch
from portfolio_fx.contracts import Candle,Rate,FXConfig,ExecutionConfig
from portfolio_fx.data import candles_asof,aggregate,aligned,rates_asof,NotReady
from portfolio_fx.signals import descriptors,signal,replay_signal
from portfolio_fx.engine import run
from portfolio_fx.metrics import summarize
from portfolio_fx.providers import normalize_yahoo,normalize_fred,fetch_fred_csv
from portfolio_fx.report import fixture,bundle,replay
from portfolio_fx.audit import encoded

T=datetime(2020,1,6,tzinfo=timezone.utc)

def candle(i,price=1.):
    start=T+timedelta(minutes=30*i); end=start+timedelta(minutes=30)
    return Candle(start,end,price,price,price,price,end,end,'test','EURUSD','mid')

def decision(direction):
    def build(rows,rates,time,model,config):
        return dict(signal_id='hand-case',payload=dict(direction=direction,decision_time=time.isoformat()))
    return build

class FXContractsTests(unittest.TestCase):
    def test_candle_ohlc_clock_identity(self):
        for change in (dict(low=2),dict(close=float('nan')),dict(pair='USDEUR'),dict(end=T),dict(available_at=T)):
            with self.assertRaises(ValueError): replace(candle(0),**change)
        with self.assertRaises(ValueError): replace(candle(0),start=T.replace(tzinfo=None))

    def test_rate_units_and_clocks(self):
        for value in (3.,True,float('inf')):
            with self.assertRaises(ValueError): Rate('EUR',value,T,T,T,'test')
        with self.assertRaises(ValueError): Rate('EUR',.03,T,T,T-timedelta(days=1),'test')

    def test_invalid_configuration(self):
        for change in (dict(fast_window=24),dict(mean_window=True),dict(reversion_z=0)):
            with self.assertRaises(ValueError): FXConfig(**change)
        for change in (dict(exposure_fraction=2),dict(commission_bps=-1),dict(safe_annual_rate=3)):
            with self.assertRaises(ValueError): ExecutionConfig(**change)

class FXDataTests(unittest.TestCase):
    def test_aggregate_hand_ohlc(self):
        a=replace(candle(0),open=1.,high=1.2,low=.9,close=1.1)
        b=replace(candle(1),open=1.1,high=1.3,low=1.,close=1.2)
        value=aggregate((a,b),60)[0]
        self.assertEqual([value[k] for k in ('open','high','low','close')],[1.,1.3,.9,1.2])
        self.assertEqual(value['available_at'],b.end.isoformat())

    def test_partial_and_missing_buckets_excluded(self):
        rows=tuple(candle(i) for i in range(48))
        self.assertEqual(len(aggregate(rows,1440)),1)
        self.assertFalse(aggregate(rows[:-1],1440))
        self.assertFalse(aggregate(rows[:4]+rows[5:8],240))
        self.assertFalse(aggregate(rows[:7],240))

    def test_revision_filter_before_selection(self):
        old=candle(0); late=replace(old,close=1.1,high=1.1,ingested_at=T+timedelta(days=1),available_at=T+timedelta(days=1))
        self.assertEqual(candles_asof((late,old),old.end),(old,))
        self.assertEqual(candles_asof((old,late),late.available_at),(late,))

    def test_conflict_and_duplicates(self):
        a=candle(0)
        self.assertEqual(candles_asof((a,a),a.end),(a,))
        with self.assertRaises(ValueError): candles_asof((a,replace(a,close=1.1,high=1.1)),a.end)
        with self.assertRaises(ValueError): aggregate((a,a),60)

    def test_daily_not_yet_closed(self):
        rows=tuple(candle(i) for i in range(48))
        self.assertFalse(aggregate(candles_asof(rows,rows[-2].end),1440))
        self.assertEqual(len(aggregate(candles_asof(rows,rows[-1].end),1440)),1)

    def test_download_does_not_become_historical(self):
        late=T+timedelta(days=10)
        row=replace(candle(0),ingested_at=late,available_at=late)
        self.assertFalse(candles_asof((row,),T+timedelta(days=1)))

    def test_rate_revision_observation_priority_and_staleness(self):
        eur=Rate('EUR',.03,T,T,T,'test'); usd=Rate('USD',.05,T,T,T,'test')
        future=replace(eur,value=.06,ingested_at=T+timedelta(days=2),available_at=T+timedelta(days=2))
        self.assertEqual(rates_asof((eur,usd,future),T+timedelta(days=1),10),(eur,usd))
        with self.assertRaises(NotReady): rates_asof((eur,usd),T+timedelta(days=11),10)
        with self.assertRaises(NotReady): rates_asof((eur,),T,10)

    def test_fred_percentage_conversion_and_capture_clock(self):
        stamp=T+timedelta(days=2)
        rows=normalize_fred('observation_date,ECBDFR\n2020-01-06,3.5\n2020-01-07,.\n','ECBDFR','EUR',stamp)
        self.assertEqual(len(rows),1); self.assertEqual(rows[0].value,.035)
        self.assertEqual(rows[0].available_at,stamp)

    def test_fred_standard_transport_and_bom(self):
        from unittest.mock import MagicMock
        response=MagicMock(); response.__enter__.return_value.read.return_value=b'\xef\xbb\xbfobservation_date,ECBDFR\n2020-01-06,3.5\n'
        with patch('portfolio_fx.providers.urlopen',return_value=response) as opener:
            raw=fetch_fred_csv('ECBDFR','2020-01-01')
        self.assertTrue(raw.startswith('observation_date'))
        self.assertEqual(opener.call_args.kwargs['timeout'],30)
        self.assertIsNone(opener.call_args.args[0].get_header('Accept'))
        self.assertEqual(opener.call_args.args[0].full_url,'https://fred.stlouisfed.org/graph/fredgraph.csv?id=ECBDFR&cosd=2020-01-01')
        self.assertEqual(normalize_fred(raw,'ECBDFR','EUR',T+timedelta(days=2))[0].value,.035)

    def test_fred_transport_failure_and_size_limit(self):
        from unittest.mock import MagicMock
        with patch('portfolio_fx.providers.urlopen',side_effect=TimeoutError('test')):
            with self.assertRaises(TimeoutError): fetch_fred_csv('DFEDTARU','2020-01-01')
        response=MagicMock(); response.__enter__.return_value.read.return_value=b'x'*2_000_001
        with patch('portfolio_fx.providers.urlopen',return_value=response):
            with self.assertRaises(ValueError): fetch_fred_csv('DFEDTARU','2020-01-01')
        with self.assertRaises(ValueError): fetch_fred_csv('OTHER','2020-01-01')
        with self.assertRaises(ValueError): normalize_fred('<html>error</html>','ECBDFR','EUR',T)

    def test_yahoo_incomplete_candle_and_identity(self):
        doc=dict(symbol='EURUSD=X',currency='USD',adapter='test',ingested_at=(T+timedelta(minutes=45)).isoformat(),
                 rows=[dict(start=(T+timedelta(minutes=30*i)).isoformat(),Open=1.,High=1.,Low=1.,Close=1.) for i in range(2)])
        rows=normalize_yahoo(doc); self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].available_at,T+timedelta(minutes=45))
        with self.assertRaises(ValueError): normalize_yahoo({**doc,'currency':'EUR'})
        missing={**doc['rows'][0],**{k:None for k in ('Open','High','Low','Close')}}
        self.assertEqual(normalize_yahoo({**doc,'rows':[missing]+doc['rows']}),rows)
        with self.assertRaises(ValueError): normalize_yahoo({**doc,'rows':[{**doc['rows'][0],'Close':None}]})

class FXSignalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rows,cls.rates=fixture()

    def test_descriptors_by_hand(self):
        value=descriptors([1.,2.,3.,4.],FXConfig(fast_window=2,slow_window=4,mean_window=4))
        self.assertEqual(value['fast_sma'],3.5); self.assertEqual(value['slow_sma'],2.5)
        self.assertAlmostEqual(value['trend'],.4); self.assertEqual(value['momentum'],3.)
        self.assertAlmostEqual(value['z'],1.5/math.sqrt(1.25))
        self.assertEqual(descriptors([1.]*4,FXConfig(fast_window=2,slow_window=4,mean_window=4))['z'],0)

    def test_future_price_and_rate_suffix_invariance(self):
        time=self.rows[479].end
        for model in ('trend','mean_reversion','rate_differential'):
            full=signal(self.rows,self.rates,time,model)
            prefix=signal(tuple(r for r in self.rows if r.end<=time),tuple(r for r in self.rates if r.available_at<=time),time,model)
            self.assertEqual(full,prefix)
            self.assertTrue(all(r['available_at']<=time for r in full['payload']['market_inputs']))

    def test_signal_direction_hand_and_plan_not_executable(self):
        time=self.rows[479].end
        for trend,z,model,want in ((.01,0,'trend',1),(-.01,0,'trend',-1),(0,2,'mean_reversion',-1),(0,-2,'mean_reversion',1)):
            with patch('portfolio_fx.signals.descriptors',return_value={'trend':trend,'z':z}):
                value=signal(self.rows,self.rates,time,model)['payload']
            self.assertEqual(value['direction'],want); self.assertFalse(value['executable']); self.assertIsNone(value['stop'])

    def test_rate_direction_and_missing(self):
        time=self.rows[479].end
        rates=(Rate('EUR',.04,time,time,time,'test'),Rate('USD',.03,time,time,time,'test'))
        value=signal(self.rows,rates,time,'rate_differential')['payload']
        self.assertEqual(value['direction'],1); self.assertAlmostEqual(value['features']['policy_rate_differential'],.01)
        self.assertEqual(signal(self.rows,(),time,'rate_differential')['payload']['state'],'NO_TRADE')

    def test_stale_insufficient_and_benchmark(self):
        self.assertEqual(signal(self.rows[:4],(),self.rows[3].end,'trend')['payload']['state'],'NO_TRADE')
        self.assertEqual(signal(self.rows,(),self.rows[-1].end+timedelta(days=5),'trend')['payload']['state'],'NO_TRADE')
        self.assertEqual(signal(self.rows,self.rates,self.rows[479].end,'no_trade')['payload']['direction'],0)
        with self.assertRaises(ValueError): signal(self.rows,(),T,'invented')

    def test_ready_and_no_trade_proposal_replay(self):
        time=self.rows[479].end
        for rows,rates,model in ((self.rows,self.rates,'trend'),(self.rows,(),'rate_differential'),(self.rows[:4],(),'trend')):
            saved=json.loads(encoded(signal(rows,rates,time,model)))
            self.assertEqual(replay_signal(saved)['status'],'verified')
        saved['payload']['direction']=1
        with self.assertRaises(ValueError): replay_signal(saved)

class FXEngineTests(unittest.TestCase):
    def path(self):
        rows=[candle(i) for i in range(10)]
        rows[-1]=replace(rows[-1],close=1.01,high=1.01)
        return tuple(rows)

    def evaluate(self,direction,execution=None,rows=None):
        rows=rows or self.path()
        settings=execution or ExecutionConfig(commission_bps=0,half_spread_bps=0,slippage_bps=0,safe_annual_rate=0,long_carry_annual_rate=0,short_carry_annual_rate=0)
        with patch('portfolio_fx.engine.signal',side_effect=decision(direction)):
            return run(rows,(),'trend',rows[0].start,rows[-1].end,execution=settings)

    def test_signed_profit_and_strict_execution_delay(self):
        for direction,nav in ((1,10010.),(-1,9990.),(0,10000.)):
            result=self.evaluate(direction); self.assertAlmostEqual(result['final_nav'],nav)
            if direction:
                self.assertEqual(result['fills'][0]['time'],(T+timedelta(hours=4,minutes=30)).isoformat())
                self.assertEqual(result['trades'][0]['holding_hours'],.5)
                self.assertAlmostEqual(result['trades'][0]['net_pnl'],nav-10000)

    def test_both_sides_cost_hand_case(self):
        cfg=ExecutionConfig(commission_bps=100,half_spread_bps=0,slippage_bps=0,safe_annual_rate=0,long_carry_annual_rate=0,short_carry_annual_rate=0)
        value=self.evaluate(1,cfg)
        self.assertAlmostEqual(value['final_nav'],9989.91008991009)
        self.assertAlmostEqual(value['totals']['commission'],20.07992007992008)

    def test_spread_slippage_and_short_fill_side(self):
        cfg=ExecutionConfig(commission_bps=0,half_spread_bps=1,slippage_bps=2,safe_annual_rate=0,long_carry_annual_rate=0,short_carry_annual_rate=0)
        value=self.evaluate(-1,cfg); fill=value['fills'][0]
        self.assertAlmostEqual(fill['execution_price'],.9997)
        self.assertAlmostEqual(fill['slippage'],2*fill['spread'])
        self.assertLess(value['final_nav'],9990)

    def test_safe_income_and_signed_carry(self):
        flat=tuple(candle(i) for i in range(10))
        cfg=ExecutionConfig(commission_bps=0,half_spread_bps=0,slippage_bps=0,safe_annual_rate=0,long_carry_annual_rate=-.365,short_carry_annual_rate=.365)
        self.assertAlmostEqual(self.evaluate(1,cfg,flat)['totals']['carry'],-1000/48000)
        self.assertAlmostEqual(self.evaluate(-1,cfg,flat)['totals']['carry'],1000/48000)
        cfg=replace(cfg,safe_annual_rate=.365)
        self.assertAlmostEqual(self.evaluate(0,cfg,flat)['final_nav'],10000*(1+1/48000)**10)

    def test_reject_late_vintage_and_duplicates(self):
        rows=self.path()
        with self.assertRaises(ValueError): self.evaluate(1,rows=(replace(rows[0],ingested_at=T+timedelta(days=1),available_at=T+timedelta(days=1)),)+rows[1:])
        with self.assertRaises(ValueError): self.evaluate(1,rows=(rows[0],)+rows)

    def test_cost_sensitivity_and_reconciliation(self):
        rows,rates=fixture(); first,last=rows[384].start,rows[575].end
        low=run(rows,rates,'trend',first,last)
        high=run(rows,rates,'trend',first,last,execution=ExecutionConfig(commission_bps=5,half_spread_bps=5,slippage_bps=5))
        self.assertGreater(high['totals']['costs'],low['totals']['costs']); self.assertLess(high['final_nav'],low['final_nav'])
        self.assertAlmostEqual(sum(t['net_pnl'] for t in low['trades'])+low['totals']['safe_income'],low['final_nav']-10000)
        self.assertGreater(summarize(low)['completed_trades'],0)

    def test_engine_future_suffix_invariance(self):
        rows,rates=fixture(); end=rows[575].end
        full=run(rows,rates,'trend',rows[384].start,end)
        prefix=run(rows[:576],rates,'trend',rows[384].start,end)
        self.assertEqual(full,prefix)

    def test_no_trade_metrics_are_defined_or_null(self):
        value=self.evaluate(0); metrics=summarize(value)
        self.assertEqual(metrics['net_return'],0); self.assertEqual(metrics['maximum_drawdown'],0)
        self.assertIsNone(metrics['profit_factor']); self.assertIsNone(metrics['sharpe_zero_rate'])
        self.assertEqual(metrics['exposure_time'],0)

    def test_expired_order_cannot_enter_after_gap(self):
        rows=tuple(candle(i) for i in list(range(8))+[13,14])
        value=self.evaluate(1,rows=rows)
        self.assertFalse(value['fills']); self.assertEqual(value['final_nav'],10000.)

    def test_same_direction_holds_and_reversal_closes_first(self):
        rows=tuple(candle(i) for i in range(26))
        held=self.evaluate(1,rows=rows)
        self.assertEqual(len(held['trades']),1); self.assertEqual(len(held['fills']),2)
        def changing(rows,rates,time,model,config):
            return decision(1 if time.hour==4 else -1 if time.hour==8 else 0)(rows,rates,time,model,config)
        with patch('portfolio_fx.engine.signal',side_effect=changing):
            value=run(rows,(),'trend',rows[0].start,rows[-1].end,
                      execution=ExecutionConfig(commission_bps=0,half_spread_bps=0,slippage_bps=0,safe_annual_rate=0,long_carry_annual_rate=0,short_carry_annual_rate=0))
        self.assertEqual([r['direction'] for r in value['trades']],[1,-1])
        self.assertEqual(len(value['fills']),4); self.assertEqual(value['final_nav'],10000.)

    def test_metrics_hand_case(self):
        result=self.evaluate(0)
        result.update(events=[dict(time=(T+timedelta(days=1)).isoformat(),nav=10100),dict(time=(T+timedelta(days=2)).isoformat(),nav=9898)],
                      final_nav=9898,elapsed_seconds=2*86400,
                      trades=[dict(net_pnl=100,holding_hours=2),dict(net_pnl=-202,holding_hours=4)])
        metrics=summarize(result)
        self.assertAlmostEqual(metrics['net_return'],-.0102)
        self.assertAlmostEqual(metrics['maximum_drawdown'],.02)
        self.assertEqual(metrics['hit_rate'],.5); self.assertEqual(metrics['expectancy_usd'],-51)
        self.assertAlmostEqual(metrics['profit_factor'],100/202)
        self.assertEqual(metrics['average_holding_hours'],3)
        self.assertAlmostEqual(metrics['cagr'],.9898**(365/2)-1)
        self.assertEqual(metrics['daily_observations'],2)
        self.assertAlmostEqual(metrics['sharpe_zero_rate'],-.005/(.03/math.sqrt(2))*math.sqrt(252))
        self.assertAlmostEqual(metrics['sortino_zero_mar'],-.005/math.sqrt(.0004/2)*math.sqrt(252))
        self.assertAlmostEqual(metrics['calmar'],(.9898**(365/2)-1)/.02)
        self.assertAlmostEqual(metrics['win_loss_ratio'],100/202)

    def test_costs_cannot_create_negative_collateral(self):
        rows=list(self.path()); rows[-1]=replace(rows[-1],close=1.8,high=1.8)
        cfg=ExecutionConfig(exposure_fraction=1,commission_bps=9000,half_spread_bps=0,slippage_bps=0,safe_annual_rate=0,long_carry_annual_rate=0,short_carry_annual_rate=0)
        with self.assertRaises(ValueError): self.evaluate(-1,cfg,tuple(rows))

    def test_bundle_replay_and_tamper(self):
        rows,rates=fixture()
        request=dict(candles=[asdict(r) for r in rows],rates=[asdict(r) for r in rates],model='mean_reversion',start=rows[384].start,end=rows[575].end,config=asdict(FXConfig()),execution=asdict(ExecutionConfig()))
        value=bundle(request)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'run.json'; path.write_bytes(encoded(value)); self.assertEqual(replay(path)['status'],'verified')
            value['payload']['result']['final_nav']+=1; path.write_bytes(encoded(value))
            with self.assertRaises(ValueError): replay(path)

if __name__=='__main__': unittest.main()
