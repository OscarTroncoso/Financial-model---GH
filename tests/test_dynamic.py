from dataclasses import replace
import math
import unittest

from portfolio_lab.config import LabConfig
from portfolio_lab.dynamic import (inverse_volatility_multiplier, drawdown_modifier,
                                  eppi_raw_multiplier, estimate_dynamic_multiplier)
from portfolio_lab.engine import run
from portfolio_lab.metrics import expected_shortfall, sharpe_ratio
from portfolio_lab.scenarios import daily_path


def config(**kw):
    return replace(LabConfig(initial_capital=100, monthly_contribution=0,
        safe_annual_return=0, commission_bps=0, half_spread_bps=0, slippage_bps=0,
        rebalance_band=0, emergency_enabled=False), **kw)


class DynamicFormulaTests(unittest.TestCase):
    def test_inverse_volatility_units_normalization_and_caps(self):
        cfg=config()
        self.assertEqual(inverse_volatility_multiplier(.15,cfg),3)
        self.assertEqual(inverse_volatility_multiplier(.30,cfg),1.5)
        self.assertEqual(inverse_volatility_multiplier(0,cfg),5)
        self.assertEqual(inverse_volatility_multiplier(100,config(min_multiplier=1)),1)

    def test_drawdown_inverse_relative_aversion_by_hand(self):
        self.assertEqual(drawdown_modifier(0,.2),1)
        self.assertEqual(drawdown_modifier(.1,.2),.5)
        self.assertEqual(drawdown_modifier(.2,.2),0)
        self.assertEqual(drawdown_modifier(.3,.2),0)
        self.assertEqual(drawdown_modifier(0,0),0)

    def test_adaptive_composition_before_clipping(self):
        estimate=estimate_dynamic_multiplier([0]*5,.15,.1,config(),'adaptive')
        self.assertEqual(estimate.value,1.5)
        self.assertEqual(estimate.drawdown_factor,.5)
        self.assertEqual(estimate.regime_factor,1)
        # Unclipped vol multiplier 9, times .5 = 4.5 (not 5*.5).
        estimate=estimate_dynamic_multiplier([0]*5,.05,.1,config(),'adaptive')
        self.assertAlmostEqual(estimate.value,4.5)

    def test_drawdown_limit_overrides_minimum(self):
        for limit,dd in ((.2,.2),(.2,.3),(0,0)):
            e=estimate_dynamic_multiplier([0]*5,.15,dd,config(min_multiplier=1,max_drawdown=limit),'adaptive')
            self.assertEqual(e.value,0)
            self.assertEqual(e.status,'drawdown_limit')

    def test_eppi_discrete_equation_by_hand(self):
        self.assertEqual(eppi_raw_multiplier([],3,2),3)
        self.assertAlmostEqual(eppi_raw_multiplier([.1],3,2),3.242)
        self.assertAlmostEqual(eppi_raw_multiplier([.1,-.1],3,2),3.08)
        self.assertEqual(eppi_raw_multiplier([0,0],3,2),3)
        # Round-trip price is NOT a round-trip additive multiplier.
        self.assertNotAlmostEqual(eppi_raw_multiplier([1,-.5],3,2),3)

    def test_eppi_cap_does_not_overwrite_raw_state(self):
        a=estimate_dynamic_multiplier([1],None,0,config(),'eppi')
        b=estimate_dynamic_multiplier([1,-.5],None,0,config(),'eppi')
        self.assertEqual(a.value,5)
        self.assertEqual(a.raw_multiplier,11)
        self.assertEqual(b.raw_multiplier,10.75)
        self.assertEqual(b.value,5)

    def test_eppi_negative_raw_state_long_only(self):
        e=estimate_dynamic_multiplier([-.3]*30,None,0,config(),'eppi')
        self.assertLess(e.raw_multiplier,0)
        self.assertEqual(e.value,0)

    def test_default_is_absorbing_even_outside_window(self):
        for model in ('eppi','adaptive','volatility_adaptive'):
            e=estimate_dynamic_multiplier([-1]+[.1]*50,.2,0,config(),model)
            self.assertEqual(e.value,0)
            self.assertEqual(e.status,'asset_default')

    def test_bad_inputs_and_unverified_parameters_rejected(self):
        for values in ({'multiplier_elasticity':2},{'regime_factor':.5},
                       {'eppi_exponent':1},{'eppi_initial_multiplier':1},
                       {'expected_shortfall_confidence':1}):
            with self.subTest(values=values),self.assertRaises(ValueError):config(**values)
        for r in (-1.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): eppi_raw_multiplier([r],3,2)
        with self.assertRaises(ValueError):eppi_raw_multiplier([1e200],3,2)
        with self.assertRaises(ValueError):drawdown_modifier(-.1,.2)
        with self.assertRaises(ValueError):inverse_volatility_multiplier(-.1,config())


class DynamicTimingTests(unittest.TestCase):
    def test_warmup_does_not_trigger_unscheduled_entry(self):
        for model in ('volatility_adaptive','adaptive'):
            events=run(daily_path([0]*30,0),config(),model).events
            self.assertEqual(events[0].multiplier_estimate.status,'warmup')
            self.assertTrue(all(e.risky==0 for e in events[:20]))
            first=next(i for i,e in enumerate(events) if e.risky>0)
            self.assertEqual(events[first].executed_reason,'monthly')
            self.assertEqual(events[first-1].decision_reason,'monthly')

    def test_eppi_initial_delay_and_daily_monitoring(self):
        events=run(daily_path([0,.1,0],0),config(),'eppi').events
        self.assertEqual(events[0].risky,0)
        self.assertAlmostEqual(events[1].risky,60)
        self.assertAlmostEqual(events[2].portfolio_value,106)
        self.assertAlmostEqual(events[2].multiplier,3.242)
        self.assertEqual(events[2].trade_amount,0)
        self.assertEqual(events[2].decision_reason,'monitor')

    def test_future_changes_cannot_change_prefix(self):
        prefix=[0,.01,-.01]*15
        for model in ('eppi','adaptive','volatility_adaptive'):
            a=run(daily_path(prefix+[.5,.2],0),config(),model).events
            b=run(daily_path(prefix+[-.5,-.2],0),config(),model).events
            self.assertEqual(a[:len(prefix)+1],b[:len(prefix)+1])

    def test_deposit_does_not_reset_eppi_or_create_drawdown(self):
        for model in ('eppi','adaptive','volatility_adaptive'):
            events=run(daily_path([0]*45,0),config(monthly_contribution=100),model).events
            self.assertTrue(all(e.drawdown==0 and e.wealth_index==1 for e in events))
            self.assertEqual(events[-1].portfolio_value,300)
            if model=='eppi':self.assertTrue(all(e.multiplier==3 for e in events))

    def test_floor_policies_and_target_caps(self):
        for model in ('eppi','adaptive','volatility_adaptive'):
            for policy in ('capital','tipp','drawdown'):
                events=run(daily_path([0,.05,-.03]*20,0),config(floor_policy=policy,max_risky_fraction=.4),model).events
                for e in events:
                    self.assertLessEqual(e.allowed_risky_budget,e.portfolio_value*.4+1e-9)
                    self.assertGreaterEqual(e.safe,0)
                    if e.pending_weight is not None:self.assertLessEqual(e.pending_weight,.4+1e-12)

    def test_default_cannot_reenter_after_deposit(self):
        for model in ('eppi','adaptive','volatility_adaptive'):
            events=run(daily_path([0]*24+[-1]+[.1]*30,0),config(monthly_contribution=100,max_risky_fraction=.8),model).events
            self.assertTrue(all(e.risky==0 and e.multiplier==0 for e in events[25:]))

    def test_drawdown_limit_exits_with_one_observation_delay(self):
        events=run(daily_path([0]*24+[-.1,0,0],0),config(max_drawdown=.01),'adaptive').events
        self.assertGreater(events[25].risky,0)
        self.assertEqual(events[25].multiplier_estimate.status,'drawdown_limit')
        self.assertEqual(events[26].risky,0)
        self.assertEqual(events[26].executed_reason,'risk_estimate_exit')

    def test_pending_eppi_buy_vetoed_when_budget_falls(self):
        events=run(daily_path([-.2,0],0),config(),'eppi').events
        self.assertEqual(events[1].executed_reason,'cancelled_buy_risk_budget')
        self.assertEqual(events[1].risky,0)

    def test_total_exhaustion_aborts_instead_of_creating_returns(self):
        with self.assertRaisesRegex(ValueError,'exhausted'):
            run(daily_path([0]*24+[-1],0),config(),'volatility_adaptive')

    def test_gap_after_entry_can_breach_floor_before_exit(self):
        # Place shock well AFTER monthly entry; avoid attributing a missed
        # shock during warmup/delayed entry to successful insurance.
        for model in ('eppi','adaptive','volatility_adaptive'):
            events=run(daily_path([0]*30+[-.5,0],0),config(emergency_enabled=True),model).events
            self.assertGreater(events[30].risky,0)
            self.assertTrue(events[31].floor_breach)
            self.assertGreater(events[31].risky,0)
            self.assertEqual(events[32].risky,0)

    def test_same_inputs_reproduce(self):
        path=daily_path([.01,-.02,.005]*20,0)
        for model in ('eppi','adaptive','volatility_adaptive'):
            self.assertEqual(run(path,config(),model),run(path,config(),model))


class TailMetricsTests(unittest.TestCase):
    def test_fractional_tail_mass_not_threshold_average(self):
        # Losses 4,3,2,1 percent; worst 37.5%=1.5 observations.
        self.assertAlmostEqual(expected_shortfall([-.04,-.03,-.02,-.01],.625),(.04+.5*.03)/1.5)
        self.assertAlmostEqual(expected_shortfall([-.04,-.03,-.02,-.01],.5),.035)
        self.assertAlmostEqual(expected_shortfall([.01,.02],.99),-.01)
        self.assertAlmostEqual(expected_shortfall([-.02]*4,.75),.02)

    def test_sharpe_differential_return_by_hand(self):
        # Mean .02, sample std .01; sqrt(4)=2.
        self.assertAlmostEqual(sharpe_ratio([.01,.02,.03],4),4)
        self.assertIsNone(sharpe_ratio([0,0],252))
        self.assertIsNone(sharpe_ratio([.1],252))

    def test_invalid_metrics_fail(self):
        for values,confidence in (([],.95),([0],1),([float('nan')],.95)):
            with self.assertRaises(ValueError):expected_shortfall(values,confidence)
