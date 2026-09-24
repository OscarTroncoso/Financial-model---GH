"""Verified core equations and explicit policy helpers; see docs/MODELS.md."""

import math
from statistics import stdev
from typing import Protocol


def nonnegative(**values: float) -> None:
    """Reject nonfinite or negative monetary/risk inputs."""
    if any(not math.isfinite(v) or v < 0 for v in values.values()):
        raise ValueError(f"Expected finite nonnegative values: {values}")


def fraction(value: float) -> None:
    nonnegative(value=value)
    if value > 1:
        raise ValueError("Fraction exceeds one")


def cushion(portfolio_value: float, floor: float) -> float:
    """Spendable risk cushion in EUR, zero when the protection floor is breached."""
    nonnegative(portfolio_value=portfolio_value, floor=floor)
    return max(portfolio_value - floor, 0.0)


def high_water_mark(previous: float, portfolio_value: float, contribution: float = 0.0) -> float:
    """Flow-adjusted monetary HWM=max(previous HWM + deposit, post-deposit NAV).

    The deposit shift is a project accounting convention, not investment return.
    Withdrawals are unsupported in this first laboratory.
    """
    nonnegative(previous=previous, portfolio_value=portfolio_value, contribution=contribution)
    return max(previous + contribution, portfolio_value)


def protected_floor(reference_value: float, protected_fraction: float) -> float:
    """EUR floor alpha * reference; reference is contributed capital or HWM."""
    nonnegative(reference_value=reference_value)
    fraction(protected_fraction)
    return protected_fraction * reference_value


def drawdown_floor(high_water_mark: float, maximum_drawdown: float) -> float:
    """Same rolling floor as TIPP with alpha=1-maximum_drawdown."""
    fraction(maximum_drawdown)
    return protected_floor(high_water_mark, 1 - maximum_drawdown)


def cppi_exposure(portfolio_value: float, floor: float, multiplier: float, cap: float) -> float:
    """Black/Perold allocation m*C, clipped to a long-only NAV exposure cap."""
    nonnegative(multiplier=multiplier)
    fraction(cap)
    return min(multiplier * cushion(portfolio_value, floor), cap * portfolio_value)


def compose_multiplier(base: float, factors: tuple[float, ...], minimum: float, maximum: float) -> float:
    """Pure multiplication/clipping interface, NOT an adaptive prediction model.

    Callers must separately verify the source of each non-neutral factor.
    """
    nonnegative(base=base, minimum=minimum, maximum=maximum)
    if minimum > maximum:
        raise ValueError("Inverted bounds")
    for value in factors:
        nonnegative(factor=value)
    value = base * math.prod(factors)
    if not math.isfinite(value):
        raise ValueError("Multiplier overflow")
    return min(maximum, max(minimum, value))


def safe_period_return(annual_return: float, calendar_days: float) -> float:
    """Effective net annual rate converted on ACT/365; not a promised yield."""
    if not math.isfinite(annual_return) or annual_return <= -1 or calendar_days < 0:
        raise ValueError("Invalid safe return inputs")
    return math.expm1(math.log1p(annual_return) * calendar_days / 365)


def realized_volatility(returns: list[float], window: int, minimum: int, periods_per_year: int) -> float | None:
    """Annualized trailing sample std; caller supplies only available returns.

    None denotes insufficient observations, not zero estimated risk.
    """
    if not 2 <= minimum <= window or periods_per_year < 1:
        raise ValueError("Invalid volatility estimator settings")
    if any(not math.isfinite(r) or r < -1 for r in returns):
        raise ValueError("Invalid returns")
    sample = returns[-window:]
    return stdev(sample) * math.sqrt(periods_per_year) if len(sample) >= minimum else None


class MultiplierModel(Protocol):
    """Future sourced risk model; no inference implementation is implied."""
    def estimate(self, available_returns: tuple[float, ...]) -> float: ...


class ExposureRule(Protocol):
    """Separate challenger interface, including EPPI after source verification."""
    def exposure(self, portfolio_value: float, floor: float) -> float: ...


BLOCKED_MODELS: dict[str, str] = {}
ENABLED_MODELS = ("static", "cppi", "tipp", "drawdown", "conditional_cppi",
                  "volatility_adaptive", "adaptive", "eppi")
DYNAMIC_MODELS = ("conditional_cppi", "volatility_adaptive", "adaptive", "eppi")


def require_enabled(model: str) -> None:
    if model in BLOCKED_MODELS:
        raise ValueError(f"Model {model} BLOCKED: {BLOCKED_MODELS[model]}")
    if model not in ENABLED_MODELS:
        raise ValueError(f"Unknown model: {model}")
