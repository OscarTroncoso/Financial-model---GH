import json
from pathlib import Path
import tempfile
import unittest

from portfolio_lab.config import LabConfig, load_config


class ConfigTests(unittest.TestCase):
    def test_example_and_defaults_match(self):
        self.assertEqual(load_config("config/lab.json"), LabConfig())

    def test_bad_values_fail_closed(self):
        for values in ({"initial_capital": 0}, {"protected_fraction": 1.1},
                       {"reference_safe": .7}, {"base_multiplier": 9},
                       {"safe_annual_return": -1}, {"slippage_bps": -1},
                       {"initial_capital": float("nan")}, {"rebalance_day": True},
                       {"emergency_enabled": "false"}, {"volatility_window": 1},
                       {"floor_policy": "unknown"}, {"max_risky_fraction": .1}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                LabConfig(**values)

    def test_unknown_key_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps({"multipler": 3}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_cost_units(self):
        self.assertAlmostEqual(LabConfig().cost_rate, .0005)
