from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from portfolio_lab.config import LabConfig
from portfolio_lab.engine import run
from portfolio_lab.metrics import summarize, longest_run
from portfolio_lab.report import write_comparison, fingerprint, verify_replay
from portfolio_lab.scenarios import daily_path


class MetricsTests(unittest.TestCase):
    def config(self):
        return LabConfig(initial_capital=100,monthly_contribution=0,safe_annual_return=0,
                         commission_bps=0,half_spread_bps=0,slippage_bps=0,
                         emergency_enabled=False,base_multiplier=2)

    def test_twr_drawdown_and_floor_breach_by_hand(self):
        # Holdings 40 risky/60 safe; lose 50% twice => 100 -> 80 -> 70.
        result=run(daily_path([0,-.5,-.5],0),self.config(),'cppi')
        m=summarize(result)
        self.assertAlmostEqual(m['time_weighted_return'],-.3)
        self.assertAlmostEqual(m['maximum_drawdown'],.3)
        self.assertEqual(m['floor_breach_observations'],1)
        self.assertEqual(m['floor_breach_episodes'],1)
        self.assertEqual(m['maximum_floor_shortfall_eur'],10)
        self.assertAlmostEqual(m['protection_observation_rate'],2/3)
        self.assertAlmostEqual(m['one_way_turnover'],.4)
        self.assertAlmostEqual(m['downside_deviation_zero_target'],((.2**2+.125**2)/3*252)**.5)
        self.assertAlmostEqual(m['downside_capture_arithmetic'],(.2+.125)/2/.5)
        self.assertIsNone(m['upside_capture_arithmetic'])
        self.assertEqual(m['cash_lock_longest_observations'],0)
        self.assertAlmostEqual(m['sortino_zero_target'],(-.2-.125)/3*252/m['downside_deviation_zero_target'])
        days=(result.events[-1].timestamp-result.events[0].timestamp).days
        self.assertAlmostEqual(m['cagr_act365'],.7**(365/days)-1)
        self.assertAlmostEqual(m['calmar'],m['cagr_act365']/.3)
        self.assertAlmostEqual(m['maximum_floor_shortfall_fraction'],10/70)
        self.assertAlmostEqual(m['near_floor_observation_fraction'],2/3)
        self.assertIsNone(m['recovery_from_benchmark_trough_ratio'])

    def test_zero_returns_undefined_ratios(self):
        m=summarize(run(daily_path([0,0,0],0),self.config(),'static'))
        for name in ('time_weighted_return','cagr_act365','maximum_drawdown','annualized_volatility','costs_eur'):
            self.assertEqual(m[name],0)
        self.assertIsNone(m['sortino_zero_target'])
        self.assertIsNone(m['calmar'])
        self.assertEqual(longest_run([True,True,False,True]),2)
        self.assertAlmostEqual(m['average_risky_fraction'],.4)
        self.assertAlmostEqual(m['average_safe_fraction'],.6)

    def test_safe_return_counts_as_profit_deposit_does_not(self):
        cfg=replace(self.config(),base_multiplier=0,monthly_contribution=100)
        m=summarize(run(daily_path([0]*45,0),cfg,'cppi'))
        self.assertEqual(m['time_weighted_return'],0)
        self.assertEqual(m['final_nav'],300)
        self.assertEqual(m['cash_lock_observation_fraction'],1)

    def test_audit_bundle_replay_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'run'
            report=write_comparison(self.config(),output)
            self.assertTrue(report.exists())
            manifest=json.loads((output/'manifest.json').read_text())
            self.assertEqual(len(manifest['files']),80)
            self.assertIn('eppi',manifest['enabled_models'])
            payload=json.loads((output/'overnight_gap--cppi.json').read_text())
            self.assertEqual(payload['input_hash'],fingerprint(payload['inputs']))
            self.assertEqual(len(payload['events']),len(payload['inputs']['observations']))
            self.assertTrue((output/'source'/'engine.py').exists())
            verify_replay(output/'overnight_gap--cppi.json')
            verify_replay(output/'overnight_gap--conditional_cppi.json')
            payload['events'][2]['risky'] += 1
            (output/'tampered.json').write_text(json.dumps(payload))
            with self.assertRaises(ValueError): verify_replay(output/'tampered.json')
            with self.assertRaises(FileExistsError):
                write_comparison(self.config(),output)

    def test_all_safe_has_no_differential_sharpe(self):
        cfg=replace(self.config(),base_multiplier=0)
        result=run(daily_path([.1,-.1,.1],.01),cfg,'cppi')
        self.assertIsNone(summarize(result)['sharpe_vs_safe'])

    def test_sharpe_uses_actual_defensive_series(self):
        from statistics import mean, stdev
        from math import sqrt
        result=run(daily_path([0,.1,-.1],.01),self.config(),'static')
        # First close all-safe NAV101 then 40.4 risky /60.6 safe.
        # Next NAV44.44+61.206=105.646. Then39.996+61.81806=101.81406.
        differentials=[0,.036,101.81406/105.646-1-.01]
        expected=mean(differentials)/stdev(differentials)*sqrt(252)
        self.assertAlmostEqual(summarize(result)['sharpe_vs_safe'],expected)

    def test_upside_and_recovery_capture(self):
        result=run(daily_path([0,-.25,.5],0),self.config(),'static')
        metrics=summarize(result)
        # 40 -> 30 -> 45 in risk; portfolio 100 -> 90 -> 105.
        self.assertAlmostEqual(metrics['upside_capture_arithmetic'],(105/90-1)/.5)
        self.assertAlmostEqual(metrics['recovery_from_benchmark_trough_ratio'],(105/90-1)/.5)
