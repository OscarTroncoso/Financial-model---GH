"""Baseline policies using the phase-1 verified CPPI formula."""
from dataclasses import dataclass
import math
from .contracts import Decision, State
from portfolio_lab.rules import cppi_exposure


@dataclass(frozen=True)
class AllocationPolicy:
    model: str = "tipp"
    static_weight: float = 0.3
    protected_fraction: float = 0.8
    multiplier: float = 3.0
    risky_cap: float = 1.0
    invested_risky_share: float = 0.75
    emergency_floor_distance: float = 0.02
    emergency_excess: float = 0.05
    rebalance_band: float = 0.01

    def __post_init__(self) -> None:
        if self.model not in ("static", "cppi", "tipp"):
            raise ValueError("Unsupported baseline policy")
        for value in (self.static_weight, self.protected_fraction, self.risky_cap,
                      self.invested_risky_share, self.emergency_floor_distance,
                      self.emergency_excess, self.rebalance_band):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Policy fractions must be in [0, 1]")
        if not math.isfinite(self.multiplier) or self.multiplier < 0:
            raise ValueError("Invalid multiplier")

    def __call__(self, state: State) -> Decision | None:
        nav = state.portfolio_value
        if self.model == "static":
            target = min(self.static_weight, self.risky_cap)
        else:
            reference = state.contributed_capital if self.model == "cppi" else state.high_water_mark
            floor = self.protected_fraction * reference
            total_budget = cppi_exposure(nav, floor, self.multiplier, self.risky_cap)
            target = total_budget * self.invested_risky_share / nav
            if state.risky_value > 0 and ((nav - floor) / nav <= self.emergency_floor_distance
                    or state.risky_value - total_budget > self.emergency_excess * nav):
                return Decision(0, "emergency")
        if state.ordinary_rebalance and abs(target - state.risky_value / nav) > self.rebalance_band:
            return Decision(target, "monthly")
        return None
