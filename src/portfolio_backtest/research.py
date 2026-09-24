"""Vectorized daily-target screening, independently reconciled to event fills."""
import numpy as np
from .contracts import Bar, Settings
from .engine import validate_bars


def daily_targets(bars: tuple[Bar, ...], close_targets: tuple[float, ...],
                  settings: Settings = Settings(monthly_contribution=0)) -> dict:
    """Close targets are shifted to the next open. No exits, carry or deposits.

    Inputs must already be causal; this routine cannot certify an externally
    generated signal. Strict bar availability is checked. It is a screening
    benchmark, not final event validation. Returns NAV, costs and wealth arrays.
    """
    validate_bars(bars, settings)
    targets = np.asarray(close_targets, dtype=float)
    if targets.shape != (len(bars),) or not np.isfinite(targets).all() or ((targets < 0) | (targets > 1)).any():
        raise ValueError("One bounded close target per bar required")
    if settings.monthly_contribution or settings.stop_fraction or settings.take_profit_fraction or settings.time_stop_bars or any(b.carry_rate for b in bars):
        raise ValueError("Use event engine for flows, carry or exits")
    opens = np.array([b.open for b in bars])
    closes = np.array([b.close for b in bars])
    safe = np.array([b.safe_return for b in bars])
    weights = np.r_[0.0, targets[:-1]]
    intraday = closes / opens
    close_fraction = weights * intraday / (1 - weights + weights * intraday)
    prior_fraction = np.r_[0.0, close_fraction[:-1]]
    overnight = opens / np.r_[opens[0], closes[:-1]]
    pre_factor = prior_fraction * overnight + (1 - prior_fraction) * (1 + safe)
    if (pre_factor <= 0).any():
        raise ValueError("Portfolio depleted")
    pre_fraction = prior_fraction * overnight / pre_factor
    sign = np.where(weights >= pre_fraction, 1.0, -1.0)
    k = settings.cost_rate
    after_cost = (1 + sign * k * pre_fraction) / (1 + sign * k * weights)
    factors = pre_factor * after_cost * (1 - weights + weights * intraday)
    wealth = np.cumprod(factors)
    nav = settings.initial_cash * wealth
    prior_nav = np.r_[settings.initial_cash, nav[:-1]]
    costs = prior_nav * pre_factor * np.abs(weights * after_cost - pre_fraction) * k
    return {"nav": nav.tolist(), "wealth": wealth.tolist(), "costs": costs.tolist()}
