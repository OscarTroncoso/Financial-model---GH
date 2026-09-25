"""Markov-switching Gaussian mean/variance (order zero), not Hamilton AR(4)."""
import numpy as np
from portfolio_regimes.hmm import fit,expectation,emissions
from portfolio_regimes.contracts import RegimeConfig
from portfolio_fx.data import NotReady
from .contracts import EconometricConfig,Rejected


def mixture(probabilities: list[float],means: list[float],variances: list[float]) -> tuple[float,float]:
    """Total variance = within-state variance + between-state mean variance."""
    p,m,v=(np.asarray(x,dtype=float) for x in (probabilities,means,variances))
    if p.ndim!=1 or not len(p) or p.shape!=m.shape or p.shape!=v.shape or not np.isfinite([p,m,v]).all() or (p<0).any() or (v<0).any() or not np.isclose(p.sum(),1,atol=1e-12,rtol=0):
        raise ValueError('Invalid predictive mixture')
    mean=float(p@m); variance=float(p@(v+(m-mean)**2))
    return mean,variance


def estimate(returns: list[float],config: EconometricConfig) -> dict:
    settings=RegimeConfig(training_window=config.window,states=config.markov_states,max_iterations=config.markov_iterations,tolerance=config.markov_tolerance)
    try: model=fit(returns,settings)
    except NotReady as error: raise Rejected(str(error)) from error
    z=(np.asarray(returns)-model['center'])/model['scale']
    gamma,_,_,_=expectation(emissions(z,model['means'],model['variances']),np.asarray(model['transition']),np.asarray(model['initial']))
    shares=gamma.mean(axis=0)
    if shares.min()<config.markov_minimum_state_share: raise Rejected('insufficient_markov_state_occupancy')
    predictive=np.asarray(model['last_filtered'])@np.asarray(model['transition'])
    mean,variance=mixture(predictive.tolist(),model['return_means'],model['return_variances'])
    return dict(mean=mean,variance=variance,parameters=model,
                diagnostics=dict(state_shares=shares.tolist(),predictive_probabilities=predictive.tolist(),autoregressive_order=0),
                variance_kind='predictive_gaussian_mixture_excludes_parameter_uncertainty')
