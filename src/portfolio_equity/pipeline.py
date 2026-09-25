"""Causal covariance -> prior -> views -> constrained sleeve weights."""
from dataclasses import asdict
from datetime import datetime
import numpy as np
from portfolio_data.contracts import Datum, utc, validate_series
from .contracts import EquityConfig, ReturnRow, Universe, View
from .models import confidence_variance, equilibrium, estimate_covariance, posterior
from .math import optimize


def allocate(universe: Universe, rows: tuple[ReturnRow, ...], views: tuple[View, ...],
             decision_time: datetime, config: EquityConfig = EquityConfig()) -> dict:
    """Return a fully auditable equity-sleeve target, not a trade instruction.

    Caller pins universe and reference-weight vintages. Future rows are excluded
    before window selection. Late/current snapshots cannot appear in historical
    decisions. Future/stale views are rejected, even if confidence is zero.
    """
    time = utc(decision_time)
    n = len(universe.asset_ids)
    if universe.available_at > time:
        raise ValueError("Universe/reference weights unavailable")
    if len({v.view_id for v in views}) != len(views):
        raise ValueError("Duplicate view identifiers")
    observed = [r for r in rows if r.available_at <= time and r.observation_time <= time]
    if any(len(r.excess_returns) != n for r in rows):
        raise ValueError("Return/universe dimension mismatch")
    if any(b.observation_time <= a.observation_time for a, b in zip(observed, observed[1:])):
        raise ValueError("Return rows must be unique and chronological; select vintages upstream")
    selected = observed[-config.lookback:]
    if len(selected) < config.minimum_observations:
        raise ValueError("Insufficient available observations")
    if (time - selected[-1].observation_time).total_seconds() > config.max_age_days * 86400:
        raise ValueError("Stale returns")
    if any(not 43200 <= (b.observation_time-a.observation_time).total_seconds() <= config.max_gap_days*86400 for a,b in zip(selected,selected[1:])):
        raise ValueError("Missing return intervals")
    estimate = estimate_covariance([r.excess_returns for r in selected], config.covariance_method,
                                   config.periods_per_year, config.ewma_decay)
    sigma = np.asarray(estimate.matrix)
    prior = equilibrium(sigma, universe.benchmark_weights, config.risk_aversion)
    active = []
    for view in views:
        if len(view.pick) != n or view.available_at > time or (time-view.available_at).total_seconds() > config.max_view_age_days*86400:
            raise ValueError("Unavailable, stale or dimensionally invalid view")
        if view.confidence > 0:
            active.append(view)
    picks = np.asarray([v.pick for v in active]).reshape(len(active), n)
    omega = np.diag([confidence_variance(sigma,v.pick,config.tau,v.confidence) for v in active])
    combined = posterior(sigma, prior, config.tau, picks,
                         [v.annual_excess_return for v in active], omega)
    result = optimize(combined.mean, sigma, config.risk_aversion,
                      [config.max_asset_weight]*n, config.optimizer_tolerance, config.optimizer_iterations)
    return {"decision_time":time.isoformat(), "universe":asdict(universe),
            "config":asdict(config), "selected_returns":[asdict(r) for r in selected],
            "views":[asdict(v) for v in views], "active_view_ids":[v.view_id for v in active],
            "covariance":asdict(estimate), "prior":prior.tolist(),
            "P":picks.tolist(), "Q":[v.annual_excess_return for v in active], "Omega":omega.tolist(),
            "posterior":asdict(combined), "optimizer":asdict(result),
            "risk_matrix_choice":"estimated_covariance_not_predictive"}


def returns_from_prices(universe: Universe, series: dict[str, list[Datum]],
                        safe_prices: list[Datum], max_gap_days: int = 7) -> tuple[ReturnRow, ...]:
    """Phase-2 bridge: strictly aligned price snapshots and an explicit safe series.

    All prices must be in the account currency. Subtract the safe simple return
    to produce arithmetic excess returns. No filling, FX conversion or dropping
    unmatched dates. Availability includes both price endpoints for every asset.
    Use DataLake.as_of to select revisions before passing snapshots here.
    """
    if set(series) != set(universe.asset_ids):
        raise ValueError("Price universe mismatch")
    groups = [validate_series(series[a], max_gap_days) for a in universe.asset_ids] + [validate_series(safe_prices, max_gap_days)]
    stamps = [r.observation_time for r in groups[0]]
    for index, group in enumerate(groups):
        if [r.observation_time for r in group] != stamps:
            raise ValueError("Unaligned sessions; no automatic filling")
        if any(r.currency != universe.currency or r.basis != "adjusted_close" for r in group):
            raise ValueError("Same-currency adjusted total-return price proxies required")
        if index < len(universe.asset_ids) and any(r.instrument_id != universe.asset_ids[index] for r in group):
            raise ValueError("Instrument ID mismatch")
    result = []
    for i in range(1,len(stamps)):
        safe_return = groups[-1][i].value / groups[-1][i-1].value - 1
        excess = tuple(group[i].value/group[i-1].value-1-safe_return for group in groups[:-1])
        available = max(group[j].available_to_model_time for group in groups for j in (i-1,i))
        sources = sorted({group[j].instrument_id+"@"+group[j].ingested_at.isoformat() for group in groups for j in (i-1,i)})
        result.append(ReturnRow(stamps[i],available,excess,";".join(sources)))
    return tuple(result)
