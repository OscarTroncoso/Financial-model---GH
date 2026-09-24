"""Hand-ledger and causal execution acceptance tests for phase 3."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from portfolio_backtest.contracts import Bar, Decision, Settings, State
from portfolio_backtest.engine import run
from portfolio_backtest.policies import AllocationPolicy
from portfolio_backtest.research import daily_targets

ZERO = Settings(initial_cash=1000, monthly_contribution=0, commission_bps=0,
                half_spread_bps=0, slippage_bps=0)


def bars(prices, start=datetime(2020, 1, 28, tzinfo=timezone.utc)):
    result = []
    for i, values in enumerate(prices):
        opening = start + timedelta(days=i, hours=9)
        close = opening + timedelta(hours=7)
        o, h, l, c = (values, values, values, values) if isinstance(values, (int, float)) else values
        result.append(Bar(opening, close, close, o, h, l, c))
    return tuple(result)


def first(weight=1):
    return lambda state: Decision(weight, "initial") if len(state.available_history) == 1 else None


class BacktestTests(unittest.TestCase):
    def test_next_open_and_no_terminal_fill(self):
        result = run(bars([100, 200, 220]), first(), ZERO)
        self.assertEqual(result.events[0].units, 0)
        self.assertEqual(result.events[1].units, 5)
        self.assertEqual(result.events[2].portfolio_value, 1100)
        self.assertEqual(run(bars([100]), first(), ZERO).trades, ())

    def test_cost_and_cash_reconcile(self):
        cfg = replace(ZERO, commission_bps=100, half_spread_bps=100, slippage_bps=100)
        result = run(bars([100, 100]), first(), cfg)
        trade = result.trades[0]
        self.assertAlmostEqual(trade.units, 1000 / 103)
        self.assertEqual(trade.execution_price, 102)
        self.assertAlmostEqual(trade.commission, trade.units)
        self.assertAlmostEqual(result.events[-1].portfolio_value + trade.cost, 1000)
        self.assertAlmostEqual(result.events[-1].cash, 0)

    def test_safe_income_and_signed_carry(self):
        path = bars([100, 100, 100])
        path = path[:2] + (replace(path[2], safe_return=.02, carry_rate=.01),)
        result = run(path, first(.5), ZERO)
        self.assertEqual(result.events[-1].safe_income, 10)
        self.assertEqual(result.events[-1].carry, 5)
        self.assertEqual(result.events[-1].portfolio_value, 1005)
        credit = run(path[:2] + (replace(path[2], carry_rate=-.01),), first(.5), ZERO)
        self.assertEqual(credit.events[-1].portfolio_value, 1015)

    def test_unfunded_carry_fails(self):
        path = bars([100, 100, 100])
        with self.assertRaises(ValueError):
            run(path[:2] + (replace(path[2], carry_rate=.01),), first(), ZERO)

    def test_contribution_before_monthly_decision(self):
        seen = []
        def policy(state):
            seen.append(state)
            return Decision(.5, "monthly") if state.ordinary_rebalance else None
        result = run(bars([100] * 6), policy, replace(ZERO, monthly_contribution=100))
        self.assertEqual([e.contribution for e in result.events], [0, 0, 0, 0, 100, 0])
        self.assertEqual(seen[4].portfolio_value, 1100)
        self.assertEqual(seen[4].contributed_capital, 1100)
        self.assertEqual(result.events[-1].units, 5.5)
        self.assertEqual(result.events[-1].wealth_index, 1)
        self.assertEqual([t.bar_index for t in result.trades], [1, 5])

    def test_gap_stop_executes_at_open(self):
        result = run(bars([100, 100, 70]), first(), replace(ZERO, stop_fraction=.1))
        self.assertEqual(result.trades[-1].reason, "stop_gap")
        self.assertEqual(result.trades[-1].execution_price, 70)
        self.assertEqual(result.events[-1].portfolio_value, 700)

    def test_ambiguous_bar_stop_first(self):
        result = run(bars([100, (100, 120, 80, 100)]), first(),
                     replace(ZERO, stop_fraction=.1, take_profit_fraction=.1))
        self.assertEqual(result.trades[-1].reason, "stop")
        self.assertEqual(result.events[-1].portfolio_value, 900)

    def test_take_profit_and_gap(self):
        cfg = replace(ZERO, take_profit_fraction=.1)
        result = run(bars([100, (100, 120, 100, 115)]), first(), cfg)
        self.assertAlmostEqual(result.events[-1].portfolio_value, 1100)
        gap = run(bars([100, 100, 120]), first(), cfg)
        self.assertEqual(gap.trades[-1].reason, "take_profit_gap")
        self.assertEqual(gap.events[-1].portfolio_value, 1200)

    def test_take_limit_includes_impact(self):
        cfg = replace(ZERO, take_profit_fraction=.1, half_spread_bps=100)
        result = run(bars([100, (100, 110.5, 100, 110)]), first(), cfg)
        self.assertEqual(len(result.trades), 1)
        result = run(bars([100, (100, 112, 100, 110)]), first(), cfg)
        self.assertAlmostEqual(result.trades[-1].execution_price, 110)

    def test_time_stop_next_open(self):
        result = run(bars([100, 100, 110, 90]), first(), replace(ZERO, time_stop_bars=2))
        self.assertEqual(result.trades[-1].bar_index, 3)
        self.assertEqual(result.trades[-1].reason, "time_stop")
        self.assertEqual(result.events[-1].portfolio_value, 900)

    def test_gap_exit_cancels_pending_buy(self):
        result = run(bars([100, 100, 70]), lambda s: Decision(1, "daily"),
                     replace(ZERO, stop_fraction=.1))
        self.assertEqual(result.events[-1].order_status, "cancelled_by_exit")
        self.assertEqual(result.events[-1].units, 0)
        self.assertIsNone(result.pending)

    def test_limit_expires_at_open(self):
        policy = lambda s: Decision(1, "limit", 95) if len(s.available_history) == 1 else None
        result = run(bars([100, (100, 101, 90, 100), 90]), policy, ZERO)
        self.assertEqual(result.trades, ())
        self.assertEqual(result.events[1].order_status, "expired_limit")

    def test_limit_fill_respects_ask(self):
        policy = lambda s: Decision(1, "limit", 100) if len(s.available_history) == 1 else None
        result = run(bars([100, 100]), policy, replace(ZERO, half_spread_bps=10))
        self.assertEqual(result.trades, ())
        self.assertEqual(len(run(bars([100, 99]), policy, ZERO).trades), 1)

    def test_emergency_between_months(self):
        cfg = AllocationPolicy(model="cppi", invested_risky_share=1)
        result = run(bars([100, 100, 50, 50]), cfg, ZERO)
        self.assertEqual(result.events[2].decision['reason'], "emergency")
        self.assertEqual(result.trades[-1].bar_index, 3)
        self.assertEqual(result.events[-1].units, 0)
        self.assertEqual(result.events[-1].portfolio_value, 700)

    def test_unused_capacity_safe(self):
        result = run(bars([100, 100]), AllocationPolicy(), ZERO)
        self.assertEqual(result.events[-1].cash, 550)
        self.assertEqual(result.events[-1].units, 4.5)

    def test_historical_download_is_rejected(self):
        path = bars([100])
        with self.assertRaisesRegex(ValueError, "unavailable"):
            run((replace(path[0], available_to_model_time=path[0].close_time + timedelta(days=1)),), first(), ZERO)

    def test_prefix_invariant(self):
        path = bars([100, 101, 50, 49, 100, 200])
        full = run(path, AllocationPolicy(), ZERO)
        prefix = run(path[:3], AllocationPolicy(), ZERO)
        self.assertEqual(full.events[:3], prefix.events)
        self.assertEqual(tuple(t for t in full.trades if t.bar_index < 3), prefix.trades)

    def test_policy_receives_only_completed_bars(self):
        def policy(state):
            self.assertTrue(all(b.available_to_model_time <= state.timestamp for b in state.available_history))
            self.assertEqual(state.available_history[-1].close_time, state.timestamp)
        run(bars([100, 200]), policy, ZERO)

    def test_vector_event_parity_with_gaps_and_costs(self):
        path = bars([(100, 110, 90, 105), (120, 130, 110, 125),
                     (90, 100, 80, 95), (105, 110, 90, 100)])
        path = tuple(replace(b, safe_return=.001) for b in path)
        targets = (.5, 1, .2, 0)
        cfg = replace(ZERO, commission_bps=20, half_spread_bps=5, slippage_bps=10)
        result = run(path, lambda s: Decision(targets[len(s.available_history)-1], "daily"), cfg)
        research = daily_targets(path, targets, cfg)
        for i, event in enumerate(result.events):
            self.assertAlmostEqual(event.portfolio_value, research['nav'][i])
            self.assertAlmostEqual(sum(t.cost for t in result.trades if t.bar_index == i), research['costs'][i])

    def test_costs_material(self):
        path = bars([100] * 6)
        policy = lambda s: Decision(len(s.available_history) % 2, "roundtrip")
        free = run(path, policy, ZERO)
        costly = run(path, policy, replace(ZERO, commission_bps=100))
        self.assertEqual(free.events[-1].portfolio_value, 1000)
        self.assertLess(costly.events[-1].portfolio_value, 960)

    def test_bad_inputs(self):
        for changes in ({'initial_cash': 0}, {'commission_bps': float('nan')},
                        {'stop_fraction': 1}, {'time_stop_bars': 1.5}):
            with self.assertRaises(ValueError):
                replace(ZERO, **changes)
        for changes in ({'high': 90}, {'open': 0}, {'safe_return': -2}, {'carry_rate': float('inf')}):
            with self.assertRaises(ValueError):
                replace(bars([100])[0], **changes)
        with self.assertRaises(ValueError):
            Decision(1.1, "bad")
        with self.assertRaises(ValueError):
            run(bars([100]) * 2, first(), ZERO)
        with self.assertRaises(ValueError):
            daily_targets(bars([100]), (1,), replace(ZERO, monthly_contribution=1))
        with self.assertRaises(ValueError):
            daily_targets(bars([100]), (float('nan'),), ZERO)


class BacktestReportTests(unittest.TestCase):
    def test_replay_and_tamper(self):
        import json
        import tempfile
        from pathlib import Path
        from portfolio_backtest.report import bundle, encoded, replay
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            document = bundle(bars([100, 100, 110]), ZERO, AllocationPolicy(model="static"))
            path.write_bytes(encoded(document))
            self.assertEqual(replay(path), document['payload']['summary'])
            document['payload']['bars'][0]['close'] = 101
            path.write_bytes(encoded(document))
            with self.assertRaisesRegex(ValueError, "checksum"):
                replay(path)

    def test_flow_neutral_report(self):
        from portfolio_backtest.report import summarize
        cfg = replace(ZERO, monthly_contribution=100)
        policy = AllocationPolicy(model="static")
        summary = summarize(run(bars([100] * 6), policy, cfg), cfg, policy)
        self.assertEqual(summary['contributions'], 100)
        self.assertEqual(summary['time_weighted_return'], 0)
        self.assertEqual(summary['maximum_drawdown'], 0)

    def test_bear_drawdown_and_floor_breach(self):
        from portfolio_backtest.report import summarize
        policy = AllocationPolicy(model="cppi", invested_risky_share=1)
        summary = summarize(run(bars([100, 100, 50, 50]), policy, ZERO), ZERO, policy)
        self.assertAlmostEqual(summary['maximum_drawdown'], .3)
        self.assertEqual(summary['floor_breach_closes'], 2)

    def test_stale_and_naive_bars(self):
        path = bars([100, 100])
        late = replace(path[1], open_time=path[1].open_time + timedelta(days=10),
                       close_time=path[1].close_time + timedelta(days=10),
                       available_to_model_time=path[1].close_time + timedelta(days=10))
        with self.assertRaises(ValueError):
            run((path[0], late), first(), ZERO)
        with self.assertRaises(ValueError):
            replace(path[0], open_time=path[0].open_time.replace(tzinfo=None))

    def test_sell_limit_and_sell_costs(self):
        def policy(state):
            return Decision(1, "buy") if len(state.available_history) == 1 else Decision(0, "sell", 100)
        cfg = replace(ZERO, commission_bps=100, half_spread_bps=100)
        result = run(bars([100, 100, 100, 102]), policy, cfg)
        self.assertEqual(result.events[2].order_status, "expired_limit")
        self.assertEqual(result.trades[-1].bar_index, 3)
        self.assertAlmostEqual(result.events[-1].cash, (1000 / 102) * 102 * .98)
        self.assertAlmostEqual(result.trades[-1].execution_price, 100.98)


class BacktestClockTests(unittest.TestCase):
    def test_timezone_normalization(self):
        original = bars([100])[0]
        zone = timezone(timedelta(hours=2))
        converted = replace(original, open_time=original.open_time.astimezone(zone),
                            close_time=original.close_time.astimezone(zone),
                            available_to_model_time=original.available_to_model_time.astimezone(zone))
        self.assertEqual(converted, original)
        self.assertEqual(converted.close_time.tzinfo, timezone.utc)

    def test_vectorized_hand_example(self):
        result = daily_targets(bars([100, 200, 220]), (1, 1, 1), ZERO)
        self.assertEqual(result['nav'], [1000, 1000, 1100])
        self.assertEqual(result['costs'], [0, 0, 0])
