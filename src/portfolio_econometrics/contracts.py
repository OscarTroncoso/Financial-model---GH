"""Precommitted model orders, numerical rejection and research policies."""
from dataclasses import dataclass,asdict
from portfolio_fx.contracts import finite

MODELS=('no_change','momentum','ar','arimax','var','kalman','markov_switching','vecm')

class Rejected(ValueError):
    """A valid sample fails a predefined numerical/stability research gate."""

@dataclass(frozen=True)
class EconometricConfig:
    window: int = 60
    max_condition: float = 1e6
    maximum_root: float = .995
    minimum_scale: float = 1e-10
    maximum_standardized_coefficient: float = 10.
    maximum_forecast_sigma: float = 5.
    maximum_absolute_return: float = .10
    kalman_process_variance: float = .001
    kalman_observation_variance: float = .25
    kalman_initial_variance: float = 1.
    maximum_state_covariance: float = 100.
    markov_states: int = 2
    markov_iterations: int = 200
    markov_tolerance: float = 1e-5
    markov_minimum_state_share: float = .02
    signal_buffer: float = .0001
    maximum_age_minutes: float = 300.
    maximum_gap_hours: float = 76.
    maximum_rate_age_days: float = 10.
    minimum_forecast_coverage: float = .5
    maximum_drawdown: float = .20

    def __post_init__(self):
        for name in ('window','markov_states','markov_iterations'):
            if type(getattr(self,name)) is not int: raise ValueError('Integer model settings required')
        if self.window<30 or self.markov_states not in (2,3) or self.markov_iterations<2: raise ValueError('Invalid model window/states')
        for name,value in asdict(self).items():
            if not finite(value) or value<=0: raise ValueError(name+' must be finite and positive')
        if self.max_condition<1 or self.maximum_root>=1 or self.maximum_absolute_return>=1 or self.minimum_forecast_coverage>1 or self.maximum_drawdown>=1 or self.markov_minimum_state_share>=1/self.markov_states:
            raise ValueError('Invalid research limits')
