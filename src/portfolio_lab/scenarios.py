"""Deterministic synthetic mechanical stress paths; never historical datasets."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from .config import LabConfig
from .data import Observation


def daily_path(returns: list[float], safe_return: float | None = None) -> tuple[Observation, ...]:
    """Build weekday closes starting at a zero-return inception (no holiday model)."""
    stamp = datetime(2020, 1, 2, 16, tzinfo=timezone.utc)
    observations = [Observation(stamp, stamp, 0.0, 0.0)]
    for value in returns:
        stamp += timedelta(days=1)
        while stamp.weekday() >= 5:
            stamp += timedelta(days=1)
        observations.append(Observation(stamp, stamp, value, safe_return))
    return tuple(observations)


@dataclass(frozen=True)
class Scenario:
    name: str
    config: LabConfig
    observations: tuple[Observation, ...]


def stress_scenarios(config: LabConfig) -> tuple[Scenario, ...]:
    """Ten fixed paths exercise shock, rebound, rate and contribution accounting."""
    paths = {
        "steady_growth": [.001] * 126,
        "prolonged_bear": [-.004] * 126,
        "fast_crash_rebound": [.001] * 22 + [-.08] * 5 + [.025] * 35 + [.001] * 64,
        "overnight_gap": [.001] * 22 + [-.50] + [.002] * 103,
        "volatility_spike": [.001] * 22 + [.06, -.06] * 20 + [.001] * 64,
        "early_losses": [-.01] * 42 + [.008] * 84,
        "late_losses": [.008] * 84 + [-.01] * 42,
    }
    scenarios = [Scenario(name, config, daily_path(values)) for name, values in paths.items()]
    scenarios += [
        Scenario("negative_safe_return", config, daily_path([-.001] * 126, -.0001)),
        Scenario("high_safe_return", replace(config, safe_annual_return=.08), daily_path([0.0] * 126)),
        Scenario("large_deposits_in_drawdown", replace(config, monthly_contribution=config.initial_capital/2),
                 daily_path([-.004] * 126)),
    ]
    return tuple(scenarios)
