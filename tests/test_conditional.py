from dataclasses import replace
import math
from statistics import NormalDist
import unittest

from portfolio_lab.conditional import (quantile_multiplier, gaussian_log_quantile,
                                      estimate_conditional_multiplier)
from portfolio_lab.engine import run
from portfolio_lab.scenarios import daily_path
from test_engine import config


class ConditionalFormulaTests(unittest.TestCase):
    def test_twenty_percent_loss_implies_multiplier_five(self):
        self.assertAlmostEqual(quantile_multiplier(math.log(.8), 0, 10), 5)
        # At the threshold: cushion 20 minus exposure 100 * 20% = 0.
        self.assertAlmostEqual(20 - 20*quantile_multiplier(math.log(.8),0,10)*.2,0)

    def test_half_loss_implies_multiplier_two(self):
        self.assertEqual(quantile_multiplier(math.log(.5),0,10),2)

    def test_upper_cap_and_nonnegative_quantile(self):
        self.assertEqual(quantile_multiplier(math.log(.8),0,3),3)
        self.assertEqual(quantile_multiplier(0,0,5),5)
        self.assertEqual(quantile_multiplier(.1,0,5),5)
        self.assertEqual(quantile_multiplier(-1e-320,0,5),5)

    def test_minimum_never_overrides_risk_bound(self):
        self.assertEqual(quantile_multiplier(math.log(.5),3,5),0)

    def test_zero_cap_and_extreme_loss(self):
        self.assertEqual(quantile_multiplier(-.1,0,0),0)
        self.assertEqual(quantile_multiplier(-1000,0,5),1)

    def test_invalid_quantiles_bounds_and_probability(self):
        for value in (float('nan'),float('inf'),-float('inf')):
            with self.assertRaises(ValueError): quantile_multiplier(value,0,5)
        with self.assertRaises(ValueError): quantile_multiplier(-.1,6,5)
        for value in (0,.5,1,float('nan')):
            with self.assertRaises(ValueError): gaussian_log_quantile(.1,value)
        with self.assertRaises(ValueError): gaussian_log_quantile(-.1,.01)

    def test_gaussian_quantile_one_standard_deviation(self):
        probability=NormalDist().cdf(-1)
        self.assertAlmostEqual(gaussian_log_quantile(.2,probability),-.2)
        self.assertEqual(gaussian_log_quantile(0,.01),0)

    def test_estimated_log_std_and_horizon_by_hand(self):
        cfg=config(volatility_min_observations=2,conditional_horizon_periods=2,
                   conditional_tail_probability=NormalDist().cdf(-1),max_multiplier=10)
        estimate=estimate_conditional_multiplier([math.expm1(.1),math.expm1(-.1)],cfg)
        self.assertAlmostEqual(estimate.horizon_log_volatility,.2)
        self.assertAlmostEqual(estimate.log_return_quantile,-.2)
        self.assertAlmostEqual(estimate.value,1/(1-math.exp(-.2)))
        self.assertEqual(estimate.observations,2)
        self.assertEqual(estimate.status,'ready')

    def test_trailing_window_and_warmup(self):
        cfg=config(volatility_window=2,volatility_min_observations=2)
        self.assertEqual(estimate_conditional_multiplier([.1],cfg).status,'warmup')
        self.assertEqual(estimate_conditional_multiplier([.1],cfg).value,0)
        self.assertEqual(estimate_conditional_multiplier([9,0,0],cfg).value,cfg.max_multiplier)
        self.assertEqual(estimate_conditional_multiplier([9,0,0],cfg).observations,2)

    def test_asset_default_is_absorbing(self):
        cfg=config(volatility_window=2,volatility_min_observations=2)
        state=estimate_conditional_multiplier([-1,0,0],cfg)
        self.assertEqual(state.status,'asset_default')
        self.assertEqual(state.value,0)
        with self.assertRaises(ValueError): estimate_conditional_multiplier([float('nan')],cfg)

    def test_more_volatility_or_longer_horizon_reduces_bound(self):
        probability=.01
        calm=quantile_multiplier(gaussian_log_quantile(.1,probability),0,100)
        stress=quantile_multiplier(gaussian_log_quantile(.3,probability),0,100)
        self.assertGreater(calm,stress)
        cfg=config(volatility_min_observations=2,conditional_horizon_periods=1,max_multiplier=100)
        short=estimate_conditional_multiplier([.1,-.1],cfg)
        long=estimate_conditional_multiplier([.1,-.1],replace(cfg,conditional_horizon_periods=21))
        self.assertGreater(short.value,long.value)

    def test_configuration_validation(self):
        for values in ({'conditional_tail_probability':0},{'conditional_tail_probability':.5},
                       {'conditional_horizon_periods':0},{'conditional_horizon_periods':True},
                       {'conditional_horizon_periods':2.5}):
            with self.subTest(values=values), self.assertRaises(ValueError): config(**values)


class ConditionalIntegrationTests(unittest.TestCase):
    def test_warmup_does_not_trigger_unscheduled_purchase(self):
        result=run(daily_path([.001]*30,0),config(),'conditional_cppi')
        events=result.events
        self.assertEqual(events[0].decision_reason,'risk_estimate_warmup')
        self.assertEqual(events[5].multiplier_estimate.status,'ready')
        self.assertEqual(events[5].risky,0)
        first_fill=next(e for e in events if e.trade_amount>0)
        self.assertEqual(first_fill.executed_reason,'monthly')
        self.assertEqual(first_fill.timestamp.month,2)
        self.assertEqual(first_fill.timestamp.day,4)

    def test_volatility_updates_do_not_rebalance(self):
        events=run(daily_path([0]*24+[.1,-.1],0),config(),'conditional_cppi').events
        self.assertEqual(events[-1].trade_amount,0)
        self.assertLess(events[-1].multiplier,events[24].multiplier)
        self.assertIsNotNone(events[-1].multiplier_estimate.log_return_quantile)

    def test_floor_policy_is_respected(self):
        path=daily_path([0]*23+[.1],0)
        capital=run(path,config(floor_policy='capital'),'conditional_cppi').events[-1]
        tipp=run(path,config(floor_policy='tipp'),'conditional_cppi').events[-1]
        drawdown=run(path,config(floor_policy='drawdown'),'conditional_cppi').events[-1]
        self.assertEqual(capital.floor,80)
        self.assertGreater(tipp.floor,capital.floor)
        self.assertEqual(tipp.floor,drawdown.floor)

    def test_future_data_cannot_change_estimates_or_decisions(self):
        path=daily_path([.01,-.01]*25,0)
        prefix=run(path[:30],config(),'conditional_cppi').events
        changed=path[:30]+tuple(replace(x,risky_return=-.2) for x in path[30:])
        self.assertEqual(run(changed,config(),'conditional_cppi').events[:30],prefix)
        self.assertEqual(run(path,config(),'conditional_cppi').events[:30],prefix)

    def test_relative_returns_use_defensive_numeraire(self):
        # Equal positive returns on both assets imply zero relative volatility.
        path=daily_path([.1,.2],0)
        path=tuple(replace(x,safe_return=x.risky_return) for x in path)
        events=run(path,config(volatility_min_observations=2),'conditional_cppi').events
        self.assertEqual(events[-1].multiplier_estimate.horizon_log_volatility,0)
        self.assertEqual(events[-1].multiplier,5)

    def test_failed_numeraire_aborts_and_asset_default_blocks_buys(self):
        with self.assertRaises(ValueError):
            run(daily_path([0],-1),config(),'conditional_cppi')
        events=run(daily_path([-1]+[0]*30,0),config(),'conditional_cppi').events
        self.assertTrue(all(e.risky==0 for e in events))
        self.assertEqual(events[-1].multiplier_estimate.status,'asset_default')

    def test_bound_failure_forces_exit_even_without_optional_emergencies(self):
        cfg=config(min_multiplier=2,base_multiplier=2,max_multiplier=5)
        path=daily_path([0]*24+[-.9,0],0)
        events=run(path,cfg,'conditional_cppi').events
        self.assertGreater(events[24].risky,0)
        self.assertEqual(events[-2].multiplier_estimate.status,'below_minimum')
        self.assertEqual(events[-1].executed_reason,'risk_estimate_exit')
        self.assertEqual(events[-1].risky,0)

    def test_exposure_caps_and_emergencies_are_independent(self):
        cfg=config(max_risky_fraction=.4,emergency_enabled=True)
        events=run(daily_path([0]*24+[-.5,0],0),cfg,'conditional_cppi').events
        self.assertLessEqual(events[24].risky/events[24].portfolio_value,.4)
        self.assertIn('floor_proximity',events[-2].emergency_reasons)
        self.assertEqual(events[-1].risky,0)

    def test_stale_pending_buy_cannot_exceed_new_quantile_budget(self):
        # Feb 3 queues 100% risk after a quiet history; Feb 4's shock is observed
        # while all funds are still safe, before that queued purchase executes.
        path=list(daily_path([0]*24,0))
        i=next(i for i,x in enumerate(path) if x.timestamp.date().isoformat()=='2020-02-04')
        path[i]=replace(path[i],risky_return=-.8)
        events=run(tuple(path),config(),'conditional_cppi').events
        self.assertEqual(events[i-1].pending_weight,1)
        self.assertEqual(events[i].executed_reason,'cancelled_buy_risk_budget')
        self.assertEqual(events[i].risky,0)
        self.assertLess(events[i].allowed_risky_budget,100)
