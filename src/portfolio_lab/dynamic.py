"""Sourced components and explicitly identified laboratory compositions.

See docs/DYNAMIC_MODELS.md; these are research rules, not fitted forecasts.
"""

import math

from .conditional import MultiplierEstimate
from .config import LabConfig
from .rules import fraction, nonnegative


def inverse_volatility_multiplier(volatility: float, config: LabConfig) -> float:
    """Normalized inverse-volatility rule m0*sigma_target/max(sigma,epsilon).

    Annual decimal volatility. Normalization, epsilon and clipping are policy.
    Elasticity 1 preserves the published inverse-volatility dependence.
    """
    nonnegative(volatility=volatility)
    value = config.base_multiplier * config.volatility_target / max(volatility, config.volatility_epsilon)
    return min(config.max_multiplier, max(config.min_multiplier, value))


def drawdown_modifier(drawdown: float, limit: float) -> float:
    """Inverse relative risk aversion from Nystrup et al. (2019), eq. 6.

    gamma0/gammat=(Dmax-D)/Dmax. Clamp at zero for a reached/breached limit.
    Zero loss tolerance means no risky budget, including at inception.
    Applying this factor to a CPPI multiplier is our explicit composition.
    """
    fraction(drawdown)
    fraction(limit)
    return max(0.0, 1 - drawdown / limit) if limit else 0.0


def eppi_raw_multiplier(available_returns: list[float], initial: float, exponent: float) -> float:
    """Mancinelli/Oliva 2023 eqs. 8 and 11: eta + sum(a*(1+r)**a*r).

    eta>1, a>1; daily completed simple risky returns, no reference-price reset.
    Raw state remains unclipped, so policy caps do not change the recurrence.
    A default return -1 uses the limiting term zero; allocation handles default
    separately as absorbing. Nonfinite arithmetic fails instead of trading.
    """
    if not math.isfinite(initial) or not math.isfinite(exponent) or initial <= 1 or exponent <= 1:
        raise ValueError("EPPI eta and a must be finite and >1")
    terms = [initial]
    for value in available_returns:
        if not math.isfinite(value) or value < -1:
            raise ValueError("Invalid risky return")
        try:
            term = exponent * (1 + value) ** exponent * value
        except OverflowError as error:
            raise ValueError("EPPI arithmetic overflow") from error
        if not math.isfinite(term):
            raise ValueError("EPPI arithmetic overflow")
        terms.append(term)
    try:
        result = math.fsum(terms)
    except OverflowError as error:
        raise ValueError("EPPI arithmetic overflow") from error
    if not math.isfinite(result):
        raise ValueError("EPPI arithmetic overflow")
    return result


def estimate_dynamic_multiplier(available_returns: list[float], volatility: float | None,
                                drawdown: float, config: LabConfig, model: str) -> MultiplierEstimate:
    """Estimate only from completed returns; warmup/default overrides minimum m.

    Adaptive uses the volatility rule times a published drawdown factor, then
    clips. This project composition is not the source paper's MPC optimizer.
    The regime hook is deliberately neutral: phase 1 implements V4, not V5.
    """
    if model not in {"volatility_adaptive", "adaptive", "eppi"}:
        raise ValueError("Unknown dynamic rule")
    if any(not math.isfinite(r) or r < -1 for r in available_returns):
        raise ValueError("Invalid risky return")
    source = {"eppi": "mancinelli_oliva_2023_eq8_11",
              "volatility_adaptive": "inverse_volatility_normalized_v1",
              "adaptive": "inverse_volatility_nystrup_drawdown_composition_v1"}[model]
    metadata = dict(observations=len(available_returns), source_id=source)
    if -1 in available_returns:
        return MultiplierEstimate(0.0, "asset_default", **metadata)
    if model == "eppi":
        raw = eppi_raw_multiplier(available_returns, config.eppi_initial_multiplier, config.eppi_exponent)
        value = min(config.max_multiplier, max(config.min_multiplier, raw))
        return MultiplierEstimate(value, "ready", raw_multiplier=raw, **metadata)
    if volatility is None:
        return MultiplierEstimate(0.0, "warmup", **metadata)
    nonnegative(volatility=volatility)
    vol_factor = config.volatility_target / max(volatility, config.volatility_epsilon)
    dd_factor = drawdown_modifier(drawdown, config.max_drawdown) if model == "adaptive" else 1.0
    raw = config.base_multiplier * vol_factor * dd_factor
    if not math.isfinite(raw):
        raise ValueError("Multiplier overflow")
    value = min(config.max_multiplier, max(config.min_multiplier, raw))
    status = "ready"
    if model == "adaptive" and dd_factor == 0:
        value, status = 0.0, "drawdown_limit"
    return MultiplierEstimate(value, status, volatility_factor=vol_factor,
                              drawdown_factor=dd_factor, regime_factor=1.0,
                              raw_multiplier=raw, **metadata)
