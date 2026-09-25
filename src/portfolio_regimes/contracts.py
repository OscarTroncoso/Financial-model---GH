"""Configurable research policies, in observed four-hour trading-bar units."""
from dataclasses import dataclass
from portfolio_fx.contracts import finite

@dataclass(frozen=True)
class RegimeConfig:
    rule_window: int = 12
    trend_threshold: float = .4
    low_volatility: float = .001
    high_volatility: float = .003
    training_window: int = 60
    states: int = 2
    max_iterations: int = 200
    tolerance: float = 1e-5
    variance_floor: float = 1e-4
    maximum_age_minutes: float = 300
    maximum_gap_hours: float = 76

    def __post_init__(self):
        for name in ('rule_window','training_window','states','max_iterations'):
            if type(getattr(self,name)) is not int: raise ValueError(name+' must be integer')
        if self.rule_window<2 or self.states not in (2,3) or self.training_window<10*self.states or self.max_iterations<2:
            raise ValueError('Insufficient windows/states/iterations')
        for name in ('trend_threshold','low_volatility','high_volatility','tolerance','variance_floor','maximum_age_minutes','maximum_gap_hours'):
            value=getattr(self,name)
            if not finite(value) or value<=0: raise ValueError(name+' must be finite and positive')
        if self.trend_threshold>1 or self.low_volatility>=self.high_volatility or self.variance_floor>=1:
            raise ValueError('Invalid regime thresholds')
