from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from portfolio_lab.config import LabConfig
from portfolio_lab.data import Observation
from portfolio_lab.engine import run
from portfolio_lab.scenarios import daily_path, stress_scenarios
from portfolio_lab.rules import ENABLED_MODELS


def config(**changes):
    baseline=LabConfig(initial_capital=100, monthly_contribution=0, safe_annual_return=0,
                       commission_bps=0, half_spread_bps=0, slippage_bps=0,
                       emergency_enabled=False, rebalance_band=0, base_multiplier=2)
    return replace(baseline, **changes)


class EngineTests(unittest.TestCase):
    def test_initial_decision_is_delayed(self):
        events=run(daily_path([.5, .1], 0), config(), 'cppi').events
        self.assertEqual(events[0].risky, 0)
        self.assertEqual(events[1].portfolio_value, 100)  # Missed first risky return.
        self.assertEqual(events[1].risky, 40)
        self.assertEqual(events[2].portfolio_value, 104)
        self.assertEqual(events[2].trade_amount, 0)

    def test_monitoring_does_not_rebalance(self):
        events=run(daily_path([0, .1, .1], 0), config(), 'cppi').events
        self.assertEqual(events[2].decision_reason, 'monitor')
        self.assertEqual(events[3].trade_amount, 0)
        self.assertNotEqual(events[3].risky, events[3].allowed_risky_budget)

    def test_gap_breaches_floor_before_delayed_emergency(self):
        events=run(daily_path([0, -.5, -.5], 0), config(emergency_enabled=True), 'cppi').events
        self.assertEqual(events[2].portfolio_value, 80)
        self.assertEqual(events[2].risky, 20)
        self.assertEqual(events[2].decision_reason, 'emergency')
        self.assertEqual(events[3].portfolio_value, 70)
        self.assertTrue(events[3].floor_breach)
        self.assertEqual(events[3].risky, 0)
        self.assertEqual(events[3].executed_reason, 'emergency')

    def test_pending_buy_cancelled_on_emergency(self):
        events=run(daily_path([0], 0), config(emergency_enabled=True, emergency_floor_distance=.25), 'cppi').events
        self.assertEqual(events[0].decision_reason, 'emergency_hold_safe')
        self.assertEqual(events[1].risky, 0)

    def test_monthly_contribution_precedes_target_and_is_not_profit(self):
        events=run(daily_path([0]*45,0), config(monthly_contribution=100), 'cppi').events
        deposit=next(i for i,e in enumerate(events) if e.contribution)
        event=events[deposit]
        self.assertEqual(event.portfolio_value,200)
        self.assertEqual(event.floor,160)
        self.assertEqual(event.allowed_risky_budget,80)
        self.assertEqual(event.wealth_index,1)
        self.assertEqual(events[deposit+1].risky,80)
        self.assertEqual(events[deposit+1].trade_amount,40)
        self.assertEqual(sum(e.contribution for e in events),200)

    def test_tipp_drawdown_equivalence(self):
        path=daily_path([0,.1,-.1]*20,0)
        left=run(path,config(monthly_contribution=100),'tipp').events
        right=run(path,config(monthly_contribution=100),'drawdown').events
        for a,b in zip(left,right):
            self.assertEqual(a.floor,b.floor)
            self.assertEqual(a.portfolio_value,b.portfolio_value)

    def test_tipp_ratchet_and_capital_floor_differ(self):
        path=daily_path([0,.5,-.1],0)
        tipp=run(path,config(),'tipp').events
        cppi=run(path,config(),'cppi').events
        self.assertEqual(tipp[2].high_water_mark,120)
        self.assertEqual(tipp[2].floor,96)
        self.assertEqual(tipp[3].floor,96)
        self.assertEqual(cppi[2].floor,80)

    def test_monthly_ratchet_holds_between_rebalances(self):
        events=run(daily_path([0,.5],0),config(floor_ratchet='monthly'),'tipp').events
        self.assertEqual(events[-1].floor,80)

    def test_costs_reduce_wealth_and_reconcile(self):
        events=run(daily_path([0,0],0),config(commission_bps=100),'static').events
        fill=events[1]
        self.assertAlmostEqual(fill.portfolio_value+fill.cost,100)
        self.assertAlmostEqual(fill.wealth_index,fill.portfolio_value/100)
        self.assertGreater(fill.cost,0)

    def test_future_changes_cannot_change_past_decisions(self):
        path=daily_path([0,.01,-.02,.03]*20,0)
        early=run(path[:25],config(),'tipp').events
        changed=path[:25]+tuple(replace(x,risky_return=-.1) for x in path[25:])
        self.assertEqual(run(changed,config(),'tipp').events[:25],early)
        self.assertEqual(run(path,config(),'tipp').events[:25],early)

    def test_bad_timestamps_and_data_fail_closed(self):
        stamp=datetime(2020,1,1,tzinfo=timezone.utc)
        with self.assertRaises(ValueError): Observation(stamp,stamp+timedelta(seconds=1),0)
        with self.assertRaises(ValueError): Observation(stamp.replace(tzinfo=None),stamp,0)
        with self.assertRaises(ValueError): Observation(stamp,stamp,float('nan'))
        one=Observation(stamp,stamp,0)
        with self.assertRaises(ValueError): run((one,one),config(),'cppi')
        later=replace(one,timestamp=stamp+timedelta(days=40))
        with self.assertRaises(ValueError): run((one,later),config(),'cppi')
        with self.assertRaises(ValueError): run(daily_path([0]),config(),'eppi_original_2008')

    def test_reproducible_stress_and_accounting(self):
        for scenario in stress_scenarios(config()):
            for model in ENABLED_MODELS:
                with self.subTest(scenario=scenario.name,model=model):
                    result=run(scenario.observations,scenario.config,model)
                    self.assertEqual(result,run(scenario.observations,scenario.config,model))
                    previous=scenario.config.initial_capital
                    risky,safe=0,previous
                    for e in result.events:
                        expected=risky*(1+e.risky_return)+safe*(1+e.safe_return)+e.contribution-e.cost
                        self.assertAlmostEqual(e.portfolio_value,expected)
                        self.assertAlmostEqual(e.risky+e.safe,e.portfolio_value)
                        self.assertGreaterEqual(e.risky,0)
                        self.assertGreaterEqual(e.safe,0)
                        self.assertLessEqual(e.allowed_risky_budget,e.portfolio_value+1e-8)
                        risky,safe=e.risky,e.safe

    def test_pending_buy_veto_when_defensive_asset_loses_value(self):
        path=daily_path([0],-.3)
        events=run(path,config(emergency_enabled=True),'cppi').events
        self.assertEqual(events[0].pending_weight,.4)
        self.assertEqual(events[1].executed_reason,'cancelled_buy_emergency')
        self.assertEqual(events[1].risky,0)
        self.assertEqual(events[1].portfolio_value,70)

    def test_monthly_hwm_tracks_unratcheted_peak(self):
        events=run(daily_path([0,.5],0),config(floor_ratchet='monthly'),'tipp').events
        self.assertEqual(events[-1].high_water_mark,120)
        self.assertEqual(events[-1].floor,80)

    def test_configured_floor_selects_model(self):
        result=run(daily_path([0],0),config(floor_policy='capital'))
        self.assertEqual(result.model,'cppi')

    def test_contribution_shifts_hwm_without_erasing_drawdown(self):
        path=daily_path([0,-.5]+[0]*21,0)
        events=run(path,config(monthly_contribution=100),'tipp').events
        event=next(e for e in events if e.contribution)
        self.assertEqual(event.high_water_mark,200)
        self.assertEqual(event.portfolio_value,180)
        self.assertEqual(event.floor,160)
        self.assertAlmostEqual(event.drawdown,.2)

    def test_non_first_monthly_rebalance_day(self):
        events=run(daily_path([0]*45,0),config(monthly_contribution=100,rebalance_day=15),'cppi').events
        deposits=[e for e in events if e.contribution]
        self.assertEqual(len(deposits),1)
        self.assertEqual(deposits[0].timestamp.day,17)  # Feb 15, 2020 was Saturday.

    def test_cost_return_split_on_deposit_date(self):
        # Queue emergency on Jan 31; it fills Feb 3, after the monthly deposit.
        path=list(daily_path([0]*24,0))
        i=next(i for i,x in enumerate(path) if x.timestamp.date().isoformat()=='2020-01-31')
        path[i]=replace(path[i],risky_return=-.5)
        result=run(tuple(path),config(monthly_contribution=100,emergency_enabled=True,commission_bps=100),'cppi')
        before,after=result.events[i:i+2]
        self.assertEqual(after.contribution,100)
        self.assertEqual(after.executed_reason,'emergency')
        # Zero market return that day: cost is charged against NAV including deposit.
        self.assertAlmostEqual(after.wealth_index/before.wealth_index,1-after.cost/(before.portfolio_value+100))
