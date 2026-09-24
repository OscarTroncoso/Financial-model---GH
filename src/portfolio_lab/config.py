"""Strict, immutable configuration schema. Rates are decimal fractions, money EUR."""

from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class LabConfig:
    """Illustrative research defaults, not calibrated investment parameters.

    Safe return is annual effective, net of fund fees. Trading costs are one-way
    basis points. Floor fractions and caps are fractions of NAV. Calendar day
    rebalance requests roll to the first supplied observation on/after that day.
    """

    initial_capital: float = 10000.0
    monthly_contribution: float = 100.0
    safe_annual_return: float = 0.03
    reference_safe: float = 0.60
    reference_equity: float = 0.30
    reference_fx_capacity: float = 0.10
    risky_equity_share: float = 0.75
    floor_policy: str = "tipp"
    protected_fraction: float = 0.80
    max_drawdown: float = 0.20
    floor_ratchet: str = "daily"
    base_multiplier: float = 3.0
    min_multiplier: float = 0.0
    max_multiplier: float = 5.0
    max_risky_fraction: float = 1.0
    volatility_target: float = 0.15
    volatility_epsilon: float = 0.001
    volatility_window: int = 20
    volatility_min_observations: int = 5
    periods_per_year: int = 252
    multiplier_elasticity: float = 1.0
    regime_factor: float = 1.0
    eppi_initial_multiplier: float = 3.0
    eppi_exponent: float = 2.0
    expected_shortfall_confidence: float = 0.95
    conditional_tail_probability: float = 0.01
    conditional_horizon_periods: int = 21
    rebalance_day: int = 1
    rebalance_band: float = 0.01
    commission_bps: float = 1.0
    half_spread_bps: float = 2.0
    slippage_bps: float = 2.0
    emergency_enabled: bool = True
    emergency_floor_distance: float = 0.02
    emergency_exposure_excess: float = 0.05
    emergency_volatility: float = 0.60
    emergency_drawdown: float = 0.18
    near_floor_distance: float = 0.03
    cash_lock_fraction: float = 0.001

    def __post_init__(self) -> None:
        defaults = {field.name: field.default for field in fields(self)}
        for name, default in defaults.items():
            value = getattr(self, name)
            if isinstance(default, bool):
                if type(value) is not bool:
                    raise ValueError(f"{name} must be boolean")
            elif isinstance(default, str):
                if not isinstance(value, str):
                    raise ValueError(f"{name} must be text")
            elif isinstance(default, int):
                if type(value) is not int:
                    raise ValueError(f"{name} must be an integer")
            elif type(value) not in (int, float):
                raise ValueError(f"{name} must be numeric")
            if type(value) in (int, float) and not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.initial_capital <= 0 or self.monthly_contribution < 0:
            raise ValueError("Capital must be positive; contributions nonnegative")
        if self.safe_annual_return <= -1:
            raise ValueError("Safe annual return must exceed -100%")
        fractions = (
            "reference_safe", "reference_equity", "reference_fx_capacity",
            "risky_equity_share", "protected_fraction", "max_drawdown",
            "max_risky_fraction", "rebalance_band", "emergency_floor_distance",
            "emergency_exposure_excess", "emergency_drawdown",
            "near_floor_distance", "cash_lock_fraction",
        )
        for name in fractions:
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not math.isclose(self.reference_safe + self.reference_equity + self.reference_fx_capacity, 1):
            raise ValueError("Reference allocation must sum to one")
        if self.reference_equity + self.reference_fx_capacity > self.max_risky_fraction:
            raise ValueError("Reference risky weight exceeds hard cap")
        if not 0 <= self.min_multiplier <= self.base_multiplier <= self.max_multiplier:
            raise ValueError("Invalid multiplier bounds")
        if not 2 <= self.volatility_min_observations <= self.volatility_window:
            raise ValueError("Invalid volatility window")
        if not 0 < self.conditional_tail_probability < .5:
            raise ValueError("Conditional tail probability must be in (0, 0.5)")
        if self.conditional_horizon_periods < 1:
            raise ValueError("Conditional horizon must be positive")
        if self.periods_per_year < 1 or not 1 <= self.rebalance_day <= 28:
            raise ValueError("Invalid calendar configuration")
        for name in ("volatility_target", "volatility_epsilon", "emergency_volatility"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("multiplier_elasticity", "regime_factor",
                     "commission_bps", "half_spread_bps", "slippage_bps"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        if self.multiplier_elasticity != 1:
            raise ValueError("Only sourced inverse-volatility elasticity 1 is enabled")
        if self.regime_factor != 1:
            raise ValueError("Regime estimator is a later phase; neutral factor 1 required")
        if self.eppi_initial_multiplier <= 1 or self.eppi_exponent <= 1:
            raise ValueError("EPPI eta and exponent must exceed 1")
        if not 0 < self.expected_shortfall_confidence < 1:
            raise ValueError("Expected shortfall confidence must be in (0, 1)")
        if self.cost_rate >= 1:
            raise ValueError("One-way costs must be below 100%")
        if self.floor_policy not in {"capital", "tipp", "drawdown"}:
            raise ValueError("Unknown floor policy")
        if self.floor_ratchet not in {"daily", "monthly"}:
            raise ValueError("Unknown floor ratchet")

    @property
    def cost_rate(self) -> float:
        """One-way proportional execution cost per euro traded."""
        return (self.commission_bps + self.half_spread_bps + self.slippage_bps) / 10000

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_config(path: str | Path) -> LabConfig:
    """Reject unknown keys and malformed values rather than silently defaulting."""
    values = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        raise ValueError("Configuration must be a JSON object")
    unknown = values.keys() - {field.name for field in fields(LabConfig)}
    if unknown:
        raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
    return LabConfig(**values)
