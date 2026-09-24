"""Validated prices, execution settings and causal strategy inputs."""

from dataclasses import dataclass
from datetime import datetime, timezone
import math


def aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamps required")


@dataclass(frozen=True)
class Bar:
    """One instrument in account currency; coherent, unadjusted OHLC.

    Synthetic fixtures or certified historical vintages only. Availability is
    the time the complete bar became usable, never its download's backdate.
    Safe return accrues from the previous close to this open on prior cash;
    carry is a signed debit over that same overnight interval per unit of
    prior-close risky notional. Intraday safe accrual/carry is zero in this
    daily convention. Never pass a full close-to-close return as overnight.
    Corporate actions must be resolved upstream; no dividend double counting.
    """
    open_time: datetime
    close_time: datetime
    available_to_model_time: datetime
    open: float
    high: float
    low: float
    close: float
    safe_return: float = 0.0
    carry_rate: float = 0.0

    def __post_init__(self) -> None:
        for name in ("open_time", "close_time", "available_to_model_time"):
            value = getattr(self, name)
            aware(value)
            object.__setattr__(self, name, value.astimezone(timezone.utc))
        if not self.open_time < self.close_time <= self.available_to_model_time:
            raise ValueError("Invalid bar clock or premature availability")
        if any(not math.isfinite(p) or p <= 0 for p in (self.open, self.high, self.low, self.close)):
            raise ValueError("Positive finite OHLC required")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Inconsistent OHLC")
        if not math.isfinite(self.safe_return) or self.safe_return < -1 or not math.isfinite(self.carry_rate):
            raise ValueError("Invalid safe return or carry")


@dataclass(frozen=True)
class Settings:
    initial_cash: float = 10000.0
    monthly_contribution: float = 100.0
    commission_bps: float = 1.0
    half_spread_bps: float = 2.0
    slippage_bps: float = 2.0
    stop_fraction: float | None = None
    take_profit_fraction: float | None = None
    time_stop_bars: int | None = None
    max_gap_days: float = 7.0

    def __post_init__(self) -> None:
        values = (self.initial_cash, self.monthly_contribution, self.commission_bps,
                  self.half_spread_bps, self.slippage_bps, self.max_gap_days)
        if any(isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("Invalid execution configuration")
        if self.initial_cash <= 0 or self.max_gap_days <= 0 or self.cost_rate >= 1:
            raise ValueError("Invalid capital, gap or total cost")
        for value in (self.stop_fraction, self.take_profit_fraction):
            if value is not None and (not math.isfinite(value) or not 0 < value < 1):
                raise ValueError("Exit fractions must be in (0, 1)")
        if self.time_stop_bars is not None and (type(self.time_stop_bars) is not int or self.time_stop_bars < 1):
            raise ValueError("Positive integer time stop required")

    @property
    def cost_rate(self) -> float:
        return (self.commission_bps + self.half_spread_bps + self.slippage_bps) / 10000


@dataclass(frozen=True)
class Decision:
    """Target fraction of post-cost NAV, optionally next-open-only limit.

    Limits constrain the spread/slippage-adjusted unit execution price,
    excluding separately charged commission. Unfilled orders expire that open.
    """
    target_weight: float
    reason: str
    limit_price: float | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.target_weight) or not 0 <= self.target_weight <= 1:
            raise ValueError("Long-only unleveraged weight required")
        if not self.reason:
            raise ValueError("Audit reason required")
        if self.limit_price is not None and (not math.isfinite(self.limit_price) or self.limit_price <= 0):
            raise ValueError("Invalid limit")


@dataclass(frozen=True)
class State:
    """Information revealed to a policy at a completed close only."""
    timestamp: datetime
    portfolio_value: float
    risky_value: float
    safe_value: float
    contributed_capital: float
    high_water_mark: float
    ordinary_rebalance: bool
    available_history: tuple[Bar, ...]
