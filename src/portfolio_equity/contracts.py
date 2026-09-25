"""Universe, data and view provenance; annual excess-return convention."""
from dataclasses import asdict, dataclass
from datetime import datetime
import math
import re
from .math import vector, weights
from portfolio_data.contracts import utc


@dataclass(frozen=True)
class Universe:
    asset_ids: tuple[str, ...]
    currency: str
    benchmark_weights: tuple[float, ...]
    available_at: datetime
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_ids", tuple(self.asset_ids))
        object.__setattr__(self, "benchmark_weights", tuple(weights(self.benchmark_weights, len(self.asset_ids))))
        object.__setattr__(self, "available_at", utc(self.available_at))
        if not self.asset_ids or len(set(self.asset_ids)) != len(self.asset_ids) or not all(isinstance(a, str) and a for a in self.asset_ids):
            raise ValueError("Unique nonempty asset IDs required")
        if not re.fullmatch(r"[A-Z]{3}", self.currency) or not self.source:
            raise ValueError("Currency and benchmark/universe provenance required")


@dataclass(frozen=True)
class ReturnRow:
    observation_time: datetime
    available_at: datetime
    excess_returns: tuple[float, ...]
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "observation_time", utc(self.observation_time))
        object.__setattr__(self, "available_at", utc(self.available_at))
        object.__setattr__(self, "excess_returns", tuple(vector(self.excess_returns)))
        if self.available_at < self.observation_time or not self.source:
            raise ValueError("Return availability/provenance invalid")


@dataclass(frozen=True)
class View:
    view_id: str
    pick: tuple[float, ...]
    annual_excess_return: float
    confidence: float
    available_at: datetime
    source: str

    def __post_init__(self) -> None:
        p = vector(self.pick)
        object.__setattr__(self, "pick", tuple(p))
        object.__setattr__(self, "available_at", utc(self.available_at))
        absolute = sum(p > 0) == 1 and sum(p < 0) == 0 and math.isclose(float(p.sum()), 1, abs_tol=1e-12)
        relative = math.isclose(float(p[p > 0].sum()), 1, abs_tol=1e-12) and math.isclose(float(p[p < 0].sum()), -1, abs_tol=1e-12)
        if not (absolute or relative):
            raise ValueError("Use a one-asset absolute view or normalized relative baskets")
        if not math.isfinite(self.annual_excess_return) or not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("Invalid annual excess return or confidence")
        if not self.view_id or not self.source:
            raise ValueError("View identifier and source required")


@dataclass(frozen=True)
class EquityConfig:
    tau: float = .05
    risk_aversion: float = 2.5
    covariance_method: str = "ledoit_wolf"
    ewma_decay: float = .94
    periods_per_year: int = 252
    lookback: int = 252
    minimum_observations: int = 20
    max_age_days: float = 7
    max_gap_days: float = 7
    max_view_age_days: float = 90
    max_asset_weight: float = .6
    rebalance_band: float = .01
    protected_fraction: float = .8
    multiplier: float = 3
    risky_cap: float = 1
    equity_share: float = .75
    floor_policy: str = "tipp"
    commission_bps: float = 1
    half_spread_bps: float = 2
    slippage_bps: float = 2
    optimizer_tolerance: float = 1e-10
    optimizer_iterations: int = 20000

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if name in ("covariance_method", "floor_policy"):
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Invalid numeric configuration: " + name)
        for name in ("periods_per_year", "lookback", "minimum_observations", "optimizer_iterations"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError("Positive integer configuration required")
        if not 2 <= self.minimum_observations <= self.lookback:
            raise ValueError("Invalid observation window")
        if any(getattr(self, n) <= 0 for n in ("tau", "risk_aversion", "max_age_days", "max_gap_days", "max_view_age_days", "optimizer_tolerance")):
            raise ValueError("Positive parameters required")
        if not 0 < self.ewma_decay < 1 or self.multiplier < 0:
            raise ValueError("Invalid decay/multiplier")
        if any(not 0 <= getattr(self, n) <= 1 for n in ("max_asset_weight", "rebalance_band", "protected_fraction", "risky_cap", "equity_share")):
            raise ValueError("Invalid fraction")
        if any(getattr(self, n) < 0 for n in ("commission_bps", "half_spread_bps", "slippage_bps")):
            raise ValueError("Negative costs")
        if self.cost_rate * max(1, self.multiplier * self.equity_share) >= 1:
            raise ValueError("Costs too large for monotone execution equation")
        if self.covariance_method not in ("sample", "ewma", "ledoit_wolf") or self.floor_policy not in ("cppi", "tipp"):
            raise ValueError("Unknown model selection")

    @property
    def cost_rate(self) -> float:
        return (self.commission_bps + self.half_spread_bps + self.slippage_bps) / 10000
