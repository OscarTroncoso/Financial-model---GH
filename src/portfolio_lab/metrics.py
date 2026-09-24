"""Explicit diagnostic definitions for the deterministic insurance laboratory."""

import math
from statistics import mean, stdev

from .engine import RunResult


def longest_run(flags: list[bool]) -> int:
    """Longest consecutive sequence of true daily observation flags."""
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def expected_shortfall(returns: list[float], confidence: float) -> float:
    """Empirical CVaR of losses -r; integrate the worst 1-confidence mass.

    Fractional boundary mass handles discrete samples/ties (Rockafellar/Uryasev
    2002). Not annualized; negative ES is possible for all-positive returns.
    """
    if not returns or not math.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("Invalid expected shortfall inputs")
    if any(not math.isfinite(r) or r < -1 for r in returns):
        raise ValueError("Invalid returns")
    losses = sorted((-r for r in returns), reverse=True)
    mass = len(losses) * (1 - confidence)
    count = int(mass)
    remainder = mass - count
    return (math.fsum(losses[:count]) + (remainder * losses[count] if count < len(losses) else 0)) / mass


def sharpe_ratio(differential_returns: list[float], periods_per_year: int) -> float | None:
    """Sharpe 1994: mean differential return / sample std, sqrt(A) scaled.

    Benchmark is the observed defensive sleeve, not a promised risk-free asset.
    Undefined for fewer than two observations or zero differential variance.
    """
    if periods_per_year < 1 or any(not math.isfinite(r) for r in differential_returns):
        raise ValueError("Invalid Sharpe inputs")
    if len(differential_returns) < 2:
        return None
    deviation = stdev(differential_returns)
    return mean(differential_returns) / deviation * math.sqrt(periods_per_year) if deviation else None


def summarize(result: RunResult) -> dict[str, float | int | None]:
    """Contribution-neutral performance and observation-based protection metrics.

    Annual volatility=sample std*sqrt(A); downside=sqrt(mean(min(r,0)^2)*A).
    Sortino=mean(r)*A/downside (zero minimum acceptable return); Calmar=CAGR/MDD.
    CAGR uses ACT/365 elapsed years, also for short synthetic paths. Capture is
    ratio of arithmetic mean portfolio/benchmark returns on benchmark up/down
    days, explicitly NOT a geometric vendor capture statistic. Undefined ratios
    are None. Protection rate is a fraction of observations, not a probability.
    """
    events = result.events
    periods = events[1:]
    returns = [e.period_return for e in periods]
    annual = result.config.periods_per_year
    # Net growth ratios can differ from their identical safe benchmark by a
    # few floating-point ulps. Do not turn that cancellation noise into Sharpe.
    differential_returns = [0.0 if math.isclose(e.period_return, e.safe_return,
                            rel_tol=0.0, abs_tol=1e-15) else e.period_return-e.safe_return
                            for e in periods]
    days = (events[-1].timestamp.date() - events[0].timestamp.date()).days
    cagr = events[-1].wealth_index ** (365 / days) - 1
    downside = math.sqrt(mean(min(r, 0) ** 2 for r in returns) * annual)
    maximum_drawdown = max(e.drawdown for e in events)
    breaches = [e.floor_breach for e in periods]
    locks = [e.risky <= result.config.cash_lock_fraction * e.portfolio_value for e in periods]
    def capture(up: bool) -> float | None:
        pairs = [(e.period_return, e.risky_return) for e in periods
                 if (e.risky_return > 0 if up else e.risky_return < 0)]
        return mean(a for a, _ in pairs) / mean(b for _, b in pairs) if pairs else None
    benchmark = [1.0]
    for event in periods:
        benchmark.append(benchmark[-1] * (1 + event.risky_return))
    trough = min(range(len(benchmark)), key=benchmark.__getitem__)
    recovery = benchmark[-1] / benchmark[trough] - 1 if benchmark[trough] else 0
    recovery_participation = (events[-1].wealth_index / events[trough].wealth_index - 1) / recovery if recovery > 0 else None
    return {
        "final_nav": events[-1].portfolio_value,
        "contributed_capital": events[-1].contributed_capital,
        "time_weighted_return": events[-1].wealth_index - 1,
        "cagr_act365": cagr,
        "maximum_drawdown": maximum_drawdown,
        "annualized_volatility": stdev(returns) * math.sqrt(annual) if len(returns) > 1 else None,
        "downside_deviation_zero_target": downside,
        "sortino_zero_target": mean(returns) * annual / downside if downside else None,
        "sharpe_vs_safe": sharpe_ratio(differential_returns, annual),
        "expected_shortfall": expected_shortfall(returns, result.config.expected_shortfall_confidence),
        "expected_shortfall_confidence": result.config.expected_shortfall_confidence,
        "calmar": cagr / maximum_drawdown if maximum_drawdown else None,
        "floor_breach_observations": sum(breaches),
        "floor_breach_episodes": sum(flag and (i == 0 or not breaches[i-1]) for i, flag in enumerate(breaches)),
        "maximum_floor_shortfall_eur": max(max(e.floor-e.portfolio_value, 0) for e in periods),
        "maximum_floor_shortfall_fraction": max(max(-e.floor_distance, 0) for e in periods),
        "protection_observation_rate": 1 - mean(breaches),
        "near_floor_observation_fraction": mean(e.floor_distance <= result.config.near_floor_distance for e in periods),
        "cash_lock_observation_fraction": mean(locks),
        "cash_lock_longest_observations": longest_run(locks),
        "cash_lock_episodes": sum(flag and (i == 0 or not locks[i-1]) for i, flag in enumerate(locks)),
        "upside_capture_arithmetic": capture(True),
        "downside_capture_arithmetic": capture(False),
        "recovery_from_benchmark_trough_ratio": recovery_participation,
        "one_way_turnover": sum(abs(e.trade_amount)/(e.portfolio_value+e.cost) for e in periods),
        "costs_eur": sum(e.cost for e in periods),
        "average_risky_fraction": mean(e.risky/e.portfolio_value for e in periods),
        "average_safe_fraction": mean(e.safe/e.portfolio_value for e in periods),
    }
