"""Conditional CPPI research challenger; source and deviations: docs/CONDITIONAL_CPPI.md.

The published multiplier bound is separate from our rolling Gaussian estimator.
It is not the PROJECT_SPEC inverse-volatility formula and not a protection promise.
"""

from dataclasses import dataclass
import math
from statistics import NormalDist, stdev

from .config import LabConfig
from .rules import nonnegative


@dataclass(frozen=True)
class MultiplierEstimate:
    """Audit state; log volatility and quantile are per configured risk horizon."""
    value: float
    status: str
    observations: int
    horizon_periods: int | None = None
    horizon_log_volatility: float | None = None
    log_return_quantile: float | None = None
    source_id: str = "fixed_multiplier"
    volatility_factor: float | None = None
    drawdown_factor: float | None = None
    regime_factor: float | None = None
    raw_multiplier: float | None = None


def quantile_multiplier(log_return_quantile: float, minimum: float, maximum: float) -> float:
    """Largest permitted m with m*(1-exp(q))<=1 for negative log-return q.

    Ben Ameur/Prigent (2006), section 3.2, positive-cushion case. q is the lower
    tail of a discounted log return. For q>=0 this condition supplies no finite
    upper bound. Research policy caps at maximum; if the bound is below minimum,
    hold zero risk rather than overriding the bound. q/min/max must be finite.
    """
    nonnegative(minimum=minimum, maximum=maximum)
    if not math.isfinite(log_return_quantile) or minimum > maximum:
        raise ValueError("Invalid quantile or multiplier bounds")
    if log_return_quantile >= 0:
        return maximum
    loss = -math.expm1(log_return_quantile)
    if minimum * loss > 1:
        return 0.0
    # Avoid division overflow for a quantile arbitrarily close to zero.
    return maximum if maximum * loss <= 1 else 1 / loss


def gaussian_log_quantile(horizon_log_volatility: float, tail_probability: float) -> float:
    """Zero-mean Gaussian lower quantile z_p*sigma, in log-return units.

    This is an explicit baseline distribution assumption, not a fitted GARCH or
    empirically calibrated tail probability. p must be in (0, 0.5).
    """
    nonnegative(horizon_log_volatility=horizon_log_volatility)
    if not math.isfinite(tail_probability) or not 0 < tail_probability < .5:
        raise ValueError("Tail probability must be in (0, 0.5)")
    quantile = NormalDist().inv_cdf(tail_probability) * horizon_log_volatility
    if not math.isfinite(quantile):
        raise ValueError("Log quantile overflow")
    return quantile


def estimate_conditional_multiplier(available_excess_returns: list[float], config: LabConfig) -> MultiplierEstimate:
    """Use only trailing completed risky returns relative to the defensive asset.

    Input x=(1+risky_return)/(1+safe_return)-1. Sample std(log1p(x)), with n-1
    divisor, estimates daily log volatility. IID square-root scaling gives the
    configured horizon. The conditional log mean is fixed at zero, not the
    sample mean. Warm-up holds safe. A -100% excess return represents an asset
    default and permanently disables new exposure for this path.
    """
    for value in available_excess_returns:
        if not math.isfinite(value) or value < -1:
            raise ValueError("Invalid available excess return")
    sample = available_excess_returns[-config.volatility_window:]
    metadata = dict(observations=len(sample), horizon_periods=config.conditional_horizon_periods,
                    source_id="benameur_prigent_2006_gaussian_baseline_v1")
    if -1 in available_excess_returns:
        return MultiplierEstimate(0.0, "asset_default", **metadata)
    if len(sample) < config.volatility_min_observations:
        return MultiplierEstimate(0.0, "warmup", **metadata)
    volatility = stdev(math.log1p(value) for value in sample) * math.sqrt(config.conditional_horizon_periods)
    quantile = gaussian_log_quantile(volatility, config.conditional_tail_probability)
    multiplier = quantile_multiplier(quantile, config.min_multiplier, config.max_multiplier)
    status = "below_minimum" if multiplier == 0 and config.min_multiplier > 0 else "ready"
    return MultiplierEstimate(multiplier, status, horizon_log_volatility=volatility,
                              log_return_quantile=quantile, **metadata)
