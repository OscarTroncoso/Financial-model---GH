"""Self-financing long-only account operations with explicit proportional costs."""

from dataclasses import dataclass
import math

from .rules import fraction, nonnegative


@dataclass(frozen=True)
class Holdings:
    """Marked EUR risky/safe holdings; safe may earn a negative realized return."""
    risky: float
    safe: float

    def __post_init__(self) -> None:
        nonnegative(risky=self.risky, safe=self.safe)

    @property
    def portfolio_value(self) -> float:
        return self.risky + self.safe

    def mark(self, risky_return: float, safe_return: float) -> "Holdings":
        """Apply period simple returns to existing holdings, before new cash."""
        if any(not math.isfinite(r) or r < -1 for r in (risky_return, safe_return)):
            raise ValueError("Invalid simple return")
        return Holdings(self.risky * (1 + risky_return), self.safe * (1 + safe_return))

    def deposit(self, amount: float) -> "Holdings":
        nonnegative(amount=amount)
        return Holdings(self.risky, self.safe + amount)


@dataclass(frozen=True)
class Fill:
    holdings: Holdings
    trade_amount: float
    cost: float


def rebalance(holdings: Holdings, target_weight: float, cost_rate: float) -> Fill:
    """Reach a weight of POST-cost NAV with one net trade.

    Solve E=w*(V-k*abs(E-R)): buy E=w*(V+k*R)/(1+w*k), sell
    E=w*(V-k*R)/(1-w*k). Cost=k*abs(E-R). No leverage or round-trip
    liquidation; deposits already in safe holdings naturally fund net purchases.
    """
    fraction(target_weight)
    if not math.isfinite(cost_rate) or not 0 <= cost_rate < 1:
        raise ValueError("Invalid proportional cost")
    value, risky = holdings.portfolio_value, holdings.risky
    if value == 0:
        return Fill(holdings, 0.0, 0.0)
    buying = target_weight * value >= risky
    sign = 1 if buying else -1
    target = target_weight * (value + sign * cost_rate * risky) / (1 + sign * target_weight * cost_rate)
    trade = target - risky
    cost = abs(trade) * cost_rate
    safe = value - cost - target
    if safe < -1e-8 or target < -1e-8:
        raise ArithmeticError("Trade violates long-only accounting")
    return Fill(Holdings(max(0.0, target), max(0.0, safe)), trade, cost)
