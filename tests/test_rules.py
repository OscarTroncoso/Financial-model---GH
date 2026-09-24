import math
import unittest

from portfolio_lab.rules import (cushion, high_water_mark, protected_floor, drawdown_floor,
    cppi_exposure, compose_multiplier, safe_period_return, realized_volatility, require_enabled)
from portfolio_lab.accounting import Holdings, rebalance


class RuleTests(unittest.TestCase):
    def test_cppi_hand_example_and_cap(self):
        self.assertEqual(cushion(100, 80), 20)
        self.assertEqual(cppi_exposure(100, 80, 3, 1), 60)
        self.assertEqual(cppi_exposure(100, 80, 9, .5), 50)

    def test_zero_cushion_breach_and_zero_nav(self):
        for value in (0, 70, 80):
            self.assertEqual(cppi_exposure(value, 80, 3, 1), 0)

    def test_invalid_financial_inputs(self):
        for value in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                cushion(value, 80)
        with self.assertRaises(ValueError):
            cppi_exposure(100, 80, 3, 1.1)

    def test_flow_adjusted_hwm(self):
        self.assertEqual(high_water_mark(100, 90), 100)
        self.assertEqual(high_water_mark(100, 110), 110)
        self.assertEqual(high_water_mark(100, 190, 100), 200)

    def test_floor_equivalence(self):
        self.assertEqual(protected_floor(125, .8), 100)
        self.assertEqual(drawdown_floor(125, .2), 100)

    def test_multiplier_composition_clipping(self):
        self.assertEqual(compose_multiplier(3, (1, 1), 0, 5), 3)
        self.assertEqual(compose_multiplier(3, (.5, .5), 0, 5), .75)
        self.assertEqual(compose_multiplier(3, (2,), 0, 5), 5)
        self.assertEqual(compose_multiplier(3, (0,), 1, 5), 1)
        with self.assertRaises(ValueError):
            compose_multiplier(3, (-1,), 0, 5)

    def test_safe_effective_rate_and_negative_rate(self):
        self.assertAlmostEqual(safe_period_return(.21, 365), .21)
        self.assertAlmostEqual(safe_period_return(.21, 182.5), .1)
        self.assertAlmostEqual(safe_period_return(-.1, 365), -.1)
        self.assertEqual(safe_period_return(.03, 0), 0)

    def test_volatility_hand_example_and_warmup(self):
        self.assertIsNone(realized_volatility([.1], 2, 2, 4))
        # Mean 0, sample variance (.01+.01)/(2-1); annual factor sqrt(4).
        self.assertAlmostEqual(realized_volatility([.1, -.1], 2, 2, 4), math.sqrt(.08))
        self.assertEqual(realized_volatility([9, .1, .1], 2, 2, 4), 0)

    def test_unverified_models_cannot_execute(self):
        for model in ('eppi_original_2008', 'adaptive_ml', 'typo'):
            with self.assertRaises(ValueError):
                require_enabled(model)


class AccountingTests(unittest.TestCase):
    def test_mark_and_deposit(self):
        marked = Holdings(40, 60).mark(.1, .05)
        self.assertEqual(marked, Holdings(44, 63))
        self.assertEqual(marked.deposit(100), Holdings(44, 163))

    def test_buy_after_cost_target(self):
        fill = rebalance(Holdings(0, 100), .5, .01)
        # E=.5*(100-.01*E) => E=50/1.005.
        self.assertAlmostEqual(fill.holdings.risky, 50/1.005)
        self.assertAlmostEqual(fill.cost, fill.trade_amount*.01)
        self.assertAlmostEqual(fill.holdings.risky/fill.holdings.portfolio_value, .5)

    def test_sell_after_cost_target(self):
        fill = rebalance(Holdings(80, 20), .5, .01)
        self.assertAlmostEqual(fill.holdings.risky, 49.6/.995)
        self.assertAlmostEqual(fill.holdings.portfolio_value, 100-fill.cost)
        self.assertAlmostEqual(fill.holdings.risky/fill.holdings.portfolio_value, .5)

    def test_full_exit_and_full_investment(self):
        self.assertEqual(rebalance(Holdings(50, 50), 0, .01).holdings, Holdings(0, 99.5))
        fill=rebalance(Holdings(0, 100), 1, .01)
        self.assertAlmostEqual(fill.holdings.risky, 100/1.01)
        self.assertAlmostEqual(fill.holdings.safe, 0)

    def test_deposit_avoids_unnecessary_sale(self):
        fill=rebalance(Holdings(60, 60).deposit(100), .4, 0)
        self.assertEqual(fill.trade_amount, 28)
        self.assertEqual(fill.holdings, Holdings(88, 132))

    def test_invalid_returns_and_negative_holdings(self):
        with self.assertRaises(ValueError): Holdings(-1, 2)
        with self.assertRaises(ValueError): Holdings(1, 1).mark(-1.1, 0)
        with self.assertRaises(ValueError): rebalance(Holdings(1, 1), .5, 1)
