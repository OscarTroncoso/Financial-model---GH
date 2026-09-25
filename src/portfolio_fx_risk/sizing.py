"""Stop-first sizing in EUR units with independent USD risk/capacity limits."""
import math
from dataclasses import asdict
from portfolio_fx.contracts import ExecutionConfig,finite
from .contracts import Capacity,RiskConfig
from portfolio_fx.data import NotReady

PIP_SIZE=.0001  # EUR/USD market unit, not a portfolio tuning parameter


def stop_distance(entry: float, sigma: float, config: RiskConfig) -> float:
    """Linearized volatility distance, not a Gaussian coverage probability.

    D=max(minimum pips, S*k*sigma*sqrt(H)). H is observed 4H bars. The
    maximum fraction rejects a proposal, never silently clips an extreme stop.
    """
    if not finite(entry) or entry<=0 or not finite(sigma) or sigma<=0: raise ValueError('Positive entry and sigma required')
    distance=max(config.minimum_stop_pips*PIP_SIZE,entry*config.stop_multiplier*sigma*math.sqrt(config.stop_horizon_bars))
    if distance>=entry*config.maximum_stop_fraction: raise NotReady('stop_distance_guard')
    return distance


def size(entry: float, direction: int, distance: float, capacity: Capacity,
         risk: RiskConfig, execution: ExecutionConfig) -> dict:
    """Round DOWN; reserve both-side costs and adverse carry to the time limit.

    Conservative per-unit exit notional is S+R*D (larger of stop/TP when R<1
    handled by max). Beyond-barrier gaps or delayed time exits can exceed the
    modeled budget. Existing portfolio risk and margin cannot be overridden.
    """
    if type(direction) is not int or direction not in (-1,1) or not all(finite(x) and x>0 for x in (entry,distance)):
        raise ValueError('Invalid direction/entry/distance')
    if distance>=entry*risk.maximum_stop_fraction: raise ValueError('Stop distance outside hard guard')
    if risk.kill_switch: return dict(state='NO_TRADE',reason='kill_switch')
    if capacity.open_positions>=risk.maximum_positions: return dict(state='NO_TRADE',reason='maximum_positions')
    budget=min(capacity.fx_capital_usd*risk.risk_per_trade,
               max(0.,capacity.nav_usd*risk.maximum_portfolio_risk-capacity.open_risk_usd))
    exit_bound=entry+max(1.,risk.reward_multiple)*distance
    carry_rate=execution.long_carry_annual_rate if direction>0 else execution.short_carry_annual_rate
    costs_per_unit=execution.cost_rate*(entry+exit_bound)
    carry_per_unit=max(0.,-carry_rate)*exit_bound*risk.maximum_holding_hours/(365*24)
    loss_per_unit=distance+costs_per_unit+carry_per_unit
    free_margin=capacity.fx_capital_usd-capacity.margin_used_usd
    caps=dict(risk=budget/loss_per_unit,
        portfolio_risk=max(0.,capacity.nav_usd*risk.maximum_portfolio_risk-capacity.open_risk_usd)/(loss_per_unit+entry*execution.cost_rate*risk.maximum_portfolio_risk),
        absolute_notional=max(0.,risk.maximum_notional_usd-capacity.open_notional_usd)/entry,
        portfolio_notional=max(0.,capacity.nav_usd*risk.maximum_portfolio_notional-capacity.open_notional_usd)/(entry*(1+risk.maximum_portfolio_notional*execution.cost_rate)),
        margin=free_margin/(entry*(1/risk.maximum_fx_leverage+execution.cost_rate)),
        maximum_units=risk.maximum_units)
    units=math.floor(min(caps.values())/risk.unit_step)*risk.unit_step
    if units<risk.minimum_units: return dict(state='NO_TRADE',reason='insufficient_risk_or_capacity',risk_budget_usd=budget,caps=caps)
    stop=entry-direction*distance; take_profit=entry+direction*risk.reward_multiple*distance
    if min(stop,take_profit)<=0: raise ValueError('Nonpositive price barrier')
    return dict(state='READY',direction=direction,entry_reference=entry,stop=stop,take_profit=take_profit,
        stop_distance=distance,stop_pips=distance/PIP_SIZE,pip_value_usd=units*PIP_SIZE,
        units_eur=units,notional_usd=units*entry,margin_usd=units*entry/risk.maximum_fx_leverage,
        risk_budget_usd=budget,modeled_stop_loss_usd=units*loss_per_unit,
        round_trip_cost_reserve_usd=units*costs_per_unit,carry_reserve_usd=units*carry_per_unit,
        binding_limit=min(caps,key=caps.get),caps=caps,capacity=asdict(capacity),
        time_stop_hours=risk.maximum_holding_hours)
