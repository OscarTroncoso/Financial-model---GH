"""Explicit risk policy, volatility configuration and USD account capacity."""
from dataclasses import dataclass,asdict
from portfolio_fx.contracts import finite


@dataclass(frozen=True)
class VolatilityConfig:
    model: str = 'realized'
    window: int = 60
    seed_window: int = 12
    ewma_decay: float = .94
    garch_alpha_grid: tuple[float,...] = (.02,.05,.10,.15)
    garch_beta_grid: tuple[float,...] = (.70,.85,.90,.95)
    minimum_variance: float = 1e-12

    def __post_init__(self):
        if self.model not in ('realized','ewma','garch'): raise ValueError('Unknown volatility model')
        if type(self.window) is not int or type(self.seed_window) is not int or not 2<=self.seed_window<self.window:
            raise ValueError('Require 2 <= seed < window')
        if not finite(self.ewma_decay) or not 0<self.ewma_decay<1: raise ValueError('Decay in (0,1) required')
        if not finite(self.minimum_variance) or self.minimum_variance<=0: raise ValueError('Positive variance tolerance required')
        for key in ('garch_alpha_grid','garch_beta_grid'):
            values=tuple(getattr(self,key)); object.__setattr__(self,key,values)
            if not values or any(not finite(v) or not 0<=v<1 for v in values): raise ValueError('Invalid GARCH grid')
        if not any(a+b<1 for a in self.garch_alpha_grid for b in self.garch_beta_grid): raise ValueError('No stationary GARCH candidate')


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade: float = .01
    maximum_risk_per_trade: float = .02
    maximum_portfolio_risk: float = .02
    maximum_portfolio_notional: float = .10
    maximum_fx_leverage: float = 1.
    maximum_notional_usd: float = 100000.
    minimum_units: float = 100.
    maximum_units: float = 100000.
    unit_step: float = 100.
    stop_multiplier: float = 2.
    stop_horizon_bars: int = 1
    minimum_stop_pips: float = 5.
    maximum_stop_fraction: float = .10
    reward_multiple: float = 2.
    maximum_holding_hours: float = 48.
    maximum_entry_drift_fraction: float = .005
    maximum_positions: int = 1
    kill_switch: bool = False

    def __post_init__(self):
        for key,value in asdict(self).items():
            if key in ('kill_switch','stop_horizon_bars','maximum_positions'): continue
            if not finite(value) or value<=0: raise ValueError('Positive finite risk settings required')
        if not self.risk_per_trade<=self.maximum_risk_per_trade<=1 or self.maximum_portfolio_risk>1:
            raise ValueError('Invalid risk fractions')
        if not 0<self.maximum_portfolio_notional<=1 or not 0<self.maximum_stop_fraction<1:
            raise ValueError('Unleveraged portfolio notional / stop guard required')
        if (self.maximum_holding_hours*2)%1: raise ValueError('Time stop must align to 30-minute execution grid')
        if self.minimum_units>self.maximum_units: raise ValueError('Invalid quantity bounds')
        if type(self.stop_horizon_bars) is not int or self.stop_horizon_bars<1: raise ValueError('Positive stop horizon required')
        if type(self.maximum_positions) is not int or self.maximum_positions<1 or type(self.kill_switch) is not bool:
            raise ValueError('Invalid hard controls')


@dataclass(frozen=True)
class Capacity:
    """Caller-supplied risk capacity; USD throughout, no implicit portfolio allocation."""
    nav_usd: float
    fx_capital_usd: float
    open_risk_usd: float = 0.
    open_notional_usd: float = 0.
    margin_used_usd: float = 0.
    open_positions: int = 0

    def __post_init__(self):
        if any(not finite(v) or v<0 for k,v in asdict(self).items() if k!='open_positions'):
            raise ValueError('Nonnegative finite account values required')
        if self.nav_usd<=0 or self.fx_capital_usd>self.nav_usd or self.margin_used_usd>self.fx_capital_usd:
            raise ValueError('Invalid account capacity')
        if type(self.open_positions) is not int or self.open_positions<0: raise ValueError('Invalid open position count')
