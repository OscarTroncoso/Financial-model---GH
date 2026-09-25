"""Contribution-aware, delayed multi-asset rebalance ledger under CPPI/TIPP."""
from dataclasses import asdict, dataclass
from datetime import datetime
import math
import numpy as np
from portfolio_data.contracts import utc
from portfolio_lab.rules import cppi_exposure
from .contracts import EquityConfig
from .math import vector, weights


@dataclass(frozen=True)
class Account:
    """Marked account-currency values; net trades naturally use cash first."""
    equity_values: tuple[float, ...]
    safe_value: float
    contributed_capital: float
    high_water_mark: float

    def __post_init__(self) -> None:
        values = vector(self.equity_values)
        object.__setattr__(self,"equity_values",tuple(values))
        if (values < 0).any() or any(not math.isfinite(v) or v < 0 for v in (self.safe_value,self.contributed_capital,self.high_water_mark)):
            raise ValueError("Invalid long-only account")
        if self.portfolio_value <= 0 or self.high_water_mark < self.portfolio_value - 1e-8:
            raise ValueError("Nonpositive NAV or HWM below current NAV")

    @property
    def portfolio_value(self) -> float:
        return sum(self.equity_values) + self.safe_value

    def deposit(self, contribution: float) -> "Account":
        if not math.isfinite(contribution) or contribution < 0:
            raise ValueError("Invalid contribution")
        return Account(self.equity_values,self.safe_value+contribution,
                       self.contributed_capital+contribution,self.high_water_mark+contribution)

    def mark(self, equity_returns: tuple[float, ...], safe_return: float = 0) -> "Account":
        returns = vector(equity_returns,len(self.equity_values))
        if (returns < -1).any() or not math.isfinite(safe_return) or safe_return < -1:
            raise ValueError("Invalid simple return")
        values = np.asarray(self.equity_values)*(1+returns)
        safe = self.safe_value*(1+safe_return)
        return Account(tuple(values),safe,self.contributed_capital,max(self.high_water_mark,float(values.sum()+safe)))


@dataclass(frozen=True)
class RebalancePlan:
    decision_time: datetime
    sleeve_weights: tuple[float, ...]
    equity_fraction: float
    reason: str
    allocation_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self,"decision_time",utc(self.decision_time))
        object.__setattr__(self,"sleeve_weights",tuple(weights(self.sleeve_weights)))
        if not math.isfinite(self.equity_fraction) or not 0 <= self.equity_fraction <= 1 or not self.reason or not self.allocation_id:
            raise ValueError("Invalid plan/provenance")


def floor(account: Account, config: EquityConfig) -> float:
    reference = account.contributed_capital if config.floor_policy == "cppi" else account.high_water_mark
    return config.protected_fraction*reference


def schedule(account: Account, sleeve_weights: tuple[float,...], decision_time: datetime,
             previous_monthly_decision: datetime | None, allocation_id: str,
             config: EquityConfig = EquityConfig(), contribution: float = 0,
             emergency: bool = False) -> tuple[Account, RebalancePlan | None, dict]:
    """Monthly close decision, after contributions. Emergencies may only exit.

    Caller persists previous monthly decision even if the band suppresses trade.
    This is a ledger adapter, not a broker or a new multi-asset OHLC simulator.
    Emergency is an explicit hard-risk input, never inferred from BL opinions.
    """
    time = utc(decision_time)
    prior = utc(previous_monthly_decision) if previous_monthly_decision else None
    if prior is not None and prior >= time:
        raise ValueError("Decision clock must advance")
    ordinary = prior is None or (time.year,time.month) != (prior.year,prior.month)
    if not ordinary and contribution:
        raise ValueError("Monthly contributions require a monthly decision")
    w = weights(sleeve_weights,len(account.equity_values))
    if (w > config.max_asset_weight+1e-10).any():
        raise ValueError("Allocation exceeds hard per-asset cap")
    updated = account.deposit(contribution)
    equity_budget = config.equity_share*cppi_exposure(updated.portfolio_value,floor(updated,config),config.multiplier,config.risky_cap)
    target_fraction = 0 if emergency else equity_budget/updated.portfolio_value
    targets = w*target_fraction
    current = np.asarray(updated.equity_values)/updated.portfolio_value
    outside_band = float(np.max(np.abs(targets-current))) > config.rebalance_band
    reason = "emergency" if emergency else "monthly"
    plan = RebalancePlan(time,tuple(w),target_fraction,reason,allocation_id) if emergency or (ordinary and outside_band) else None
    audit = {"decision_time":time.isoformat(),"ordinary":ordinary,"contribution":contribution,
             "floor":floor(updated,config),"permitted_equity_budget":equity_budget,
             "sleeve_weights":w.tolist(),"full_portfolio_targets":targets.tolist(),
             "allocation_id":allocation_id,"status":"scheduled" if plan else "inside_band" if ordinary else "not_monthly"}
    return updated,plan,audit


def execute(account: Account, plan: RebalancePlan, execution_time: datetime,
            config: EquityConfig = EquityConfig()) -> tuple[Account, dict]:
    """Execute at a later observed mark, rechecking risk after costs and gaps.

    Solve x + k*sum(abs(E_i(x)-R_i)) = V for post-cost NAV x. E_i(x) uses
    the frozen sleeve mix and the lower of the planned equity fraction and
    the current CPPI/TIPP budget. Bisection is monotone under the config bound.
    Config costs are proportional reference-notional costs, as in phase 3.
    Account must already be marked to execution prices; there is no implicit
    same-close fill, price discovery, interest accrual or invented FX conversion.
    """
    time = utc(execution_time)
    if not plan.decision_time < time or (time-plan.decision_time).total_seconds() > config.max_gap_days*86400:
        raise ValueError("Execution must be later and within order lifetime")
    w = weights(plan.sleeve_weights,len(account.equity_values))
    if (w > config.max_asset_weight+1e-10).any():
        raise ValueError("Plan exceeds execution risk limits")
    value = account.portfolio_value
    boundary = floor(account,config)
    current = np.asarray(account.equity_values)
    def targets(nav: float) -> np.ndarray:
        allowed = config.equity_share*cppi_exposure(nav,boundary,config.multiplier,config.risky_cap)
        budget = min(plan.equity_fraction*nav,allowed)
        if plan.reason == "emergency":
            budget = 0
        return w*budget
    low,high = 0.0,value
    for _ in range(100):
        middle = (low+high)/2
        cost = config.cost_rate*float(np.abs(targets(middle)-current).sum())
        if middle+cost > value:
            high = middle
        else:
            low = middle
    nav = (low+high)/2
    desired = targets(nav)
    trades = desired-current
    turnover = float(np.abs(trades).sum())
    commission = turnover*config.commission_bps/10000
    spread = turnover*config.half_spread_bps/10000
    slippage = turnover*config.slippage_bps/10000
    costs = commission+spread+slippage
    safe = value-costs-float(desired.sum())
    if safe < -1e-8 or abs(value-costs-nav) > 1e-7:
        raise ArithmeticError("Execution failed self-financing checks")
    updated = Account(tuple(desired),max(0.0,safe),account.contributed_capital,account.high_water_mark)
    audit = {"decision_time":plan.decision_time.isoformat(),"execution_time":time.isoformat(),
             "allocation_id":plan.allocation_id,"reason":plan.reason,
             "pre_account":asdict(account),"post_account":asdict(updated),
             "trades":trades.tolist(),"commission":commission,"spread":spread,"slippage":slippage,
             "costs":costs,"turnover":turnover,"floor":boundary,
             "risk_cap_after_costs":config.equity_share*cppi_exposure(updated.portfolio_value,boundary,config.multiplier,config.risky_cap)}
    return updated,audit
