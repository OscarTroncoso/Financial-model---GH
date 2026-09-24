"""Small daily phase-1 harness; not the later general execution/backtest engine."""

from dataclasses import dataclass
from datetime import datetime
import math

from .accounting import Holdings, rebalance
from .config import LabConfig
from .dynamic import estimate_dynamic_multiplier
from .rules import DYNAMIC_MODELS
from .conditional import MultiplierEstimate, estimate_conditional_multiplier
from .data import Observation, validate_path
from .rules import (cppi_exposure, cushion, high_water_mark,
                    protected_floor, realized_volatility, require_enabled, safe_period_return)


@dataclass(frozen=True)
class AuditEvent:
    """End-of-observation state and actions, monetary quantities in EUR."""
    timestamp: datetime
    available_to_model_time: datetime
    model: str
    portfolio_value: float
    risky: float
    safe: float
    contribution: float
    contributed_capital: float
    high_water_mark: float
    floor: float
    cushion: float
    floor_distance: float
    floor_breach: bool
    drawdown: float
    volatility: float | None
    multiplier: float
    multiplier_estimate: MultiplierEstimate
    allowed_risky_budget: float
    exposure_gap: float
    reference_equity_capacity: float
    reference_fx_capacity: float
    trade_amount: float
    cost: float
    executed_reason: str
    decision_reason: str
    pending_weight: float | None
    emergency_reasons: tuple[str, ...]
    period_return: float
    wealth_index: float
    risky_return: float
    safe_return: float


@dataclass(frozen=True)
class RunResult:
    model: str
    config: LabConfig
    observations: tuple[Observation, ...]
    events: tuple[AuditEvent, ...]


def emergency_reasons(value: float, floor: float, risky: float, budget: float,
                      drawdown: float, volatility: float | None, config: LabConfig) -> tuple[str, ...]:
    """Configured operational full-exit policy; no claim of optimal thresholds."""
    if not config.emergency_enabled or value <= 0:
        return ()
    reasons = []
    if (value - floor) / value <= config.emergency_floor_distance:
        reasons.append("floor_proximity")
    if risky > config.max_risky_fraction * value:
        reasons.append("hard_exposure_cap")
    if risky - budget > config.emergency_exposure_excess * value:
        reasons.append("excess_exposure")
    if drawdown >= config.emergency_drawdown:
        reasons.append("drawdown")
    if volatility is not None and volatility >= config.emergency_volatility:
        reasons.append("volatility")
    return tuple(reasons)


def run(observations: tuple[Observation, ...], config: LabConfig, model: str | None = None) -> RunResult:
    """Observe -> contribute -> fill prior target -> monitor -> queue next target.

    Fill uses a previously fixed weight, not today's model target; proportional
    costs solve post-cost NAV exactly. A newly observed emergency may veto a buy,
    but newly requested emergency sales wait one observation. No terminal fill.
    """
    if model is None:
        model = {"capital": "cppi", "tipp": "tipp", "drawdown": "drawdown"}[config.floor_policy]
    require_enabled(model)
    validate_path(observations)
    holdings = Holdings(0, config.initial_capital)
    capital = hwm = config.initial_capital
    floor_policy = (config.floor_policy if model in DYNAMIC_MODELS else
                    {"static": "capital", "cppi": "capital", "tipp": "tipp", "drawdown": "drawdown"}[model])
    floor = protected_floor(capital, 1 - config.max_drawdown if floor_policy == "drawdown" else config.protected_fraction)
    wealth = wealth_peak = 1.0
    returns: list[float] = []
    excess_returns: list[float] = []
    events: list[AuditEvent] = []
    pending: tuple[float, str] | None = None
    initial_month = (observations[0].timestamp.year, observations[0].timestamp.month)
    last_rebalanced_month = initial_month
    for i, observation in enumerate(observations):
        previous_value = holdings.portfolio_value
        days = 0 if i == 0 else (observation.timestamp.date() - observations[i - 1].timestamp.date()).days
        safe_return = observation.safe_return
        if safe_return is None:
            safe_return = safe_period_return(config.safe_annual_return, days)
        holdings = holdings.mark(observation.risky_return, safe_return)
        marked_value = holdings.portfolio_value
        if previous_value <= 0 or marked_value <= 0:
            raise ValueError("Portfolio exhausted: stop simulation rather than invent returns")
        if i:
            returns.append(observation.risky_return)
        volatility = realized_volatility(returns, config.volatility_window,
                                         config.volatility_min_observations, config.periods_per_year)
        if model == "conditional_cppi":
            if safe_return <= -1:
                raise ValueError("Conditional model requires a positive defensive numeraire")
            if i:
                excess_returns.append((1 + observation.risky_return) / (1 + safe_return) - 1)
            estimate = estimate_conditional_multiplier(excess_returns, config)
        else:
            estimate = MultiplierEstimate(0.0 if model == "static" else config.base_multiplier,
                                          "static" if model == "static" else "fixed", 0)
        multiplier = estimate.value
        month = (observation.timestamp.year, observation.timestamp.month)
        ordinary = i == 0 or (month != last_rebalanced_month and observation.timestamp.day >= config.rebalance_day)
        contribution = config.monthly_contribution if ordinary and i else 0.0
        if ordinary:
            last_rebalanced_month = month
        capital += contribution
        holdings = holdings.deposit(contribution)
        contributed_value = holdings.portfolio_value
        hwm = high_water_mark(hwm, contributed_value, contribution)
        if floor_policy == "capital":
            floor = protected_floor(capital, config.protected_fraction)
        else:
            alpha = config.protected_fraction if floor_policy == "tipp" else 1 - config.max_drawdown
            floor += protected_floor(contribution, alpha)
            if config.floor_ratchet == "daily" or ordinary:
                floor = max(floor, protected_floor(hwm, alpha))
        pre_wealth = wealth * marked_value / previous_value
        pre_drawdown = 1 - pre_wealth / max(wealth_peak, pre_wealth)
        if model in {"volatility_adaptive", "adaptive", "eppi"}:
            estimate = estimate_dynamic_multiplier(returns, volatility, pre_drawdown, config, model)
            multiplier = estimate.value
        pre_budget = cppi_exposure(contributed_value, floor, multiplier, config.max_risky_fraction)
        pre_emergency = emergency_reasons(contributed_value, floor, holdings.risky, pre_budget,
                                          pre_drawdown, volatility, config) if model != "static" else ()
        cost = trade = 0.0
        executed_reason = "none"
        if pending is not None:
            weight, reason = pending
            if (pre_emergency or estimate.status in {"warmup", "asset_default", "below_minimum", "drawdown_limit"}) and weight * contributed_value > holdings.risky:
                executed_reason = "cancelled_buy_emergency"
            elif (model in DYNAMIC_MODELS and weight * contributed_value > holdings.risky
                  and weight * contributed_value > pre_budget
                  and not math.isclose(weight * contributed_value, pre_budget, rel_tol=1e-12)):
                executed_reason = "cancelled_buy_risk_budget"
            else:
                if reason == "emergency":
                    weight = min(weight, holdings.risky / contributed_value)
                fill = rebalance(holdings, min(weight, config.max_risky_fraction), config.cost_rate)
                holdings, trade, cost = fill.holdings, fill.trade_amount, fill.cost
                executed_reason = reason
            pending = None
        value = holdings.portfolio_value
        growth = (marked_value / previous_value) * (value / contributed_value)
        wealth *= growth
        wealth_peak = max(wealth_peak, wealth)
        drawdown = 1 - wealth / wealth_peak
        if model == "adaptive":
            estimate = estimate_dynamic_multiplier(returns, volatility, drawdown, config, model)
            multiplier = estimate.value
        budget = ((config.reference_equity + config.reference_fx_capacity) * value if model == "static"
                  else cppi_exposure(value, floor, multiplier, config.max_risky_fraction))
        emergency = emergency_reasons(value, floor, holdings.risky, budget, drawdown, volatility, config) if model != "static" else ()
        reason = "monitor"
        if model in DYNAMIC_MODELS and estimate.status != "ready":
            reason = "risk_estimate_" + estimate.status
            if holdings.risky > 0:
                pending = (0.0, "risk_estimate_exit")
        elif emergency:
            reason = "emergency_hold_safe"
            if holdings.risky > 0:
                pending, reason = (0.0, "emergency"), "emergency"
        elif ordinary:
            reason = "within_band"
            if abs(budget - holdings.risky) > config.rebalance_band * value:
                pending, reason = (budget / value, "initial" if i == 0 else "monthly"), "initial" if i == 0 else "monthly"
        events.append(AuditEvent(
            observation.timestamp, observation.available_to_model_time, model, value,
            holdings.risky, holdings.safe, contribution, capital, hwm, floor,
            cushion(value, floor), (value - floor) / value, value < floor,
            drawdown, volatility, multiplier, estimate,
            budget, holdings.risky - budget,
            budget * config.risky_equity_share, budget * (1 - config.risky_equity_share),
            trade, cost, executed_reason, reason, pending[0] if pending else None,
            emergency, growth - 1, wealth, observation.risky_return, safe_return,
        ))
    return RunResult(model, config, observations, tuple(events))
