"""Daily event engine with next-open execution and a self-financing ledger."""
from dataclasses import asdict, dataclass
from typing import Callable

from portfolio_lab.accounting import Holdings, rebalance
from .contracts import Bar, Decision, Settings, State


@dataclass(frozen=True)
class Trade:
    bar_index: int
    phase: str
    reason: str
    reference_price: float
    execution_price: float
    units: float
    commission: float
    spread: float
    slippage: float

    @property
    def cost(self) -> float:
        return self.commission + self.spread + self.slippage


@dataclass(frozen=True)
class Event:
    bar_index: int
    timestamp: str
    cash: float
    units: float
    portfolio_value: float
    contribution: float
    safe_income: float
    carry: float
    period_return: float
    wealth_index: float
    high_water_mark: float
    decision: dict | None
    order_status: str


@dataclass(frozen=True)
class Result:
    events: tuple[Event, ...]
    trades: tuple[Trade, ...]
    pending: Decision | None


def validate_bars(bars: tuple[Bar, ...], settings: Settings) -> None:
    if not bars:
        raise ValueError("Empty simulation")
    for i, bar in enumerate(bars):
        # Strict vintage mode: late downloads cannot inform historical closes.
        if bar.available_to_model_time > bar.close_time:
            raise ValueError("Bar unavailable at historical decision time")
        if i:
            previous = bars[i - 1]
            gap = (bar.open_time - previous.close_time).total_seconds() / 86400
            if gap <= 0 or gap > settings.max_gap_days:
                raise ValueError("Overlapping, unordered or stale bars")
            if bar.open_time.date() <= previous.open_time.date():
                raise ValueError("Daily engine requires separate UTC session dates")


def run(bars: tuple[Bar, ...], policy: Callable[[State], Decision | None],
        settings: Settings = Settings()) -> Result:
    """Long-only account. Policy sees only the completed historical prefix.

    Order: income/carry on prior holdings; pending order at open; resting
    brackets (stop first on ambiguous candles); close mark; deposit; decision.
    Gap bracket exits take priority over pending orders. No terminal forced
    sale. Costs apply to reference notional, with spread/slippage reflected in
    execution price. Stop anchors use entry reference price; additions reset
    anchors and holding age. Limits are next-open-only, not intraday fills.
    """
    validate_bars(bars, settings)
    cash, units = settings.initial_cash, 0.0
    prior_nav = capital = hwm = settings.initial_cash
    prior_close = bars[0].open
    wealth = 1.0
    pending = None
    anchor = None
    entry_index = None
    events, trades = [], []
    previous_month = (bars[0].close_time.year, bars[0].close_time.month)

    def execute(weight: float, price: float, index: int, phase: str, reason: str) -> None:
        nonlocal cash, units, anchor, entry_index
        fill = rebalance(Holdings(units * price, cash), weight, settings.cost_rate)
        quantity = fill.trade_amount / price
        if abs(quantity) < 1e-12:
            return
        impact = (settings.half_spread_bps + settings.slippage_bps) / 10000
        execution = price * (1 + (1 if quantity > 0 else -1) * impact)
        notional = abs(fill.trade_amount)
        trades.append(Trade(index, phase, reason, price, execution, quantity,
                            notional * settings.commission_bps / 10000,
                            notional * settings.half_spread_bps / 10000,
                            notional * settings.slippage_bps / 10000))
        cash = fill.holdings.safe
        units = fill.holdings.risky / price
        if quantity > 0:
            anchor, entry_index = price, index
        elif units < 1e-12:
            anchor = entry_index = None
            units = 0.0

    for i, bar in enumerate(bars):
        safe_income = cash * bar.safe_return
        carry = units * prior_close * bar.carry_rate
        cash += safe_income - carry
        if cash < 0:
            raise ValueError("Carry exhausts safe cash; leverage is disabled")
        status = "none"
        exited = False
        stop = anchor * (1 - settings.stop_fraction) if anchor is not None and settings.stop_fraction else None
        take = anchor * (1 + settings.take_profit_fraction) if anchor is not None and settings.take_profit_fraction else None
        sell_impact = (settings.half_spread_bps + settings.slippage_bps) / 10000
        if units and ((stop is not None and bar.open <= stop) or (take is not None and bar.open * (1 - sell_impact) >= take)):
            reason = "stop_gap" if stop is not None and bar.open <= stop else "take_profit_gap"
            execute(0, bar.open, i, "open", reason)
            exited, status = True, "cancelled_by_exit" if pending else "exit"
        if pending is not None and not exited:
            buying = pending.target_weight * (cash + units * bar.open) >= units * bar.open
            impact = (settings.half_spread_bps + settings.slippage_bps) / 10000
            price = bar.open * (1 + (1 if buying else -1) * impact)
            limit_ok = pending.limit_price is None or (price <= pending.limit_price if buying else price >= pending.limit_price)
            if limit_ok:
                execute(pending.target_weight, bar.open, i, "open", pending.reason)
                status = "filled"
            else:
                status = "expired_limit"
        pending = None
        stop = anchor * (1 - settings.stop_fraction) if anchor is not None and settings.stop_fraction else None
        take = anchor * (1 + settings.take_profit_fraction) if anchor is not None and settings.take_profit_fraction else None
        if units and stop is not None and bar.low <= stop:
            execute(0, stop, i, "intrabar", "stop")
            exited = True
        elif units and take is not None and bar.high >= take:
            # A resting sell limit cannot execute below its limit after impact.
            impact = (settings.half_spread_bps + settings.slippage_bps) / 10000
            reference = take / (1 - impact)
            if bar.high >= reference:
                execute(0, reference, i, "intrabar", "take_profit")
                exited = True
        nav = cash + units * bar.close
        if nav <= 0:
            raise ValueError("Portfolio depleted")
        period_return = nav / prior_nav - 1
        wealth *= 1 + period_return
        month = (bar.close_time.year, bar.close_time.month)
        ordinary = i == 0 or month != previous_month
        contribution = settings.monthly_contribution if month != previous_month else 0.0
        previous_month = month
        cash += contribution
        nav += contribution
        capital += contribution
        hwm = max(hwm + contribution, nav)
        state = State(bar.close_time, nav, units * bar.close, cash, capital, hwm,
                      ordinary, bars[:i + 1])
        decision = policy(state)
        if decision is not None and not isinstance(decision, Decision):
            raise TypeError("Policy must return a validated Decision or None")
        if units and settings.time_stop_bars is not None and i - entry_index + 1 >= settings.time_stop_bars:
            decision = Decision(0, "time_stop")
        # No same-bar reentry after a bracket exit; later monthly decisions may enter.
        if exited:
            decision = None
        pending = decision
        events.append(Event(i, bar.close_time.isoformat(), cash, units, nav, contribution,
                            safe_income, carry, period_return, wealth, hwm,
                            asdict(decision) if decision else None, status))
        prior_nav, prior_close = nav, bar.close
    return Result(tuple(events), tuple(trades), pending)
