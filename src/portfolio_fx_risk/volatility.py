"""Observed-bar log-return volatility and a restricted GARCH(1,1) challenger."""
import math
from statistics import mean,variance
from dataclasses import asdict
from portfolio_fx.contracts import Candle,finite
from portfolio_fx.data import candles_asof,aggregate,NotReady
from portfolio_data.contracts import utc
from .contracts import VolatilityConfig


def ewma_step(previous: float, innovation: float, decay: float) -> float:
    if not all(finite(x) for x in (previous,innovation,decay)) or previous<0 or not 0<decay<1: raise ValueError('Invalid EWMA inputs')
    return decay*previous+(1-decay)*innovation**2


def garch_step(previous: float, innovation: float, omega: float, alpha: float, beta: float) -> float:
    if not all(finite(x) for x in (previous,innovation,omega,alpha,beta)) or previous<=0 or omega<=0 or min(alpha,beta)<0 or alpha+beta>=1:
        raise ValueError('Stationary positive GARCH(1,1) parameters required')
    return omega+alpha*innovation**2+beta*previous


def estimate(returns: tuple[float,...], config: VolatilityConfig) -> dict:
    """One-observed-bar variance. Realized means sample historical variance.

    EWMA/GARCH assume zero conditional mean. GARCH uses variance targeting
    omega=(1-alpha-beta)*mean(r^2), then a finite configured grid minimizing
    mean(log(h)+r^2/h). This is restricted Gaussian quasi-likelihood fitting,
    not a continuous MLE or a claim that conditional normality holds.
    Initialization uses the first seed observations, excluded from likelihood.
    """
    if len(returns)!=config.window or any(not finite(r) for r in returns): raise ValueError('Exact finite return window required')
    historical=variance(returns)
    if historical<=config.minimum_variance: raise NotReady('zero_or_degenerate_volatility')
    seed=mean(r*r for r in returns[:config.seed_window])
    if config.model!='realized' and seed<=config.minimum_variance: raise NotReady('degenerate_variance_seed')
    extra={}; h=historical
    if config.model=='ewma':
        h=seed
        for r in returns[config.seed_window:]: h=ewma_step(h,r,config.ewma_decay)
    elif config.model=='garch':
        target=mean(r*r for r in returns); candidates=[]
        for a in config.garch_alpha_grid:
            for b in config.garch_beta_grid:
                if a+b>=1: continue
                omega=(1-a-b)*target; current=seed; scores=[]
                for r in returns[config.seed_window:]:
                    scores.append(math.log(current)+r*r/current)
                    current=garch_step(current,r,omega,a,b)
                candidates.append(dict(alpha=a,beta=b,omega=omega,score=mean(scores),next_variance=current))
        best=min(candidates,key=lambda c:(c['score'],c['alpha'],c['beta']))
        h=best['next_variance']; extra=dict(fit='variance_targeted_finite_grid',parameters=best,candidates=candidates,variance_target=target)
    if not finite(h) or h<=config.minimum_variance: raise NotReady('invalid_variance_forecast')
    return dict(model=config.model,variance=h,sigma=math.sqrt(h),sample_variance=historical,
                seed_variance=seed,unit='squared_log_return_per_observed_4H_bar',**extra)


def forecast(rows: tuple[Candle,...], time, config: VolatilityConfig, max_age_minutes: float=300,
             max_gap_hours: float=76) -> dict:
    time=utc(time); known=candles_asof(rows,time); bars=aggregate(known,240)[-(config.window+1):]
    if len(bars)!=config.window+1: raise NotReady('insufficient_volatility_history')
    if (time-utc(bars[-1]['end'])).total_seconds()>max_age_minutes*60: raise NotReady('stale_volatility_input')
    if any((utc(b['start'])-utc(a['end'])).total_seconds()>max_gap_hours*3600 for a,b in zip(bars,bars[1:])):
        raise NotReady('volatility_history_gap')
    returns=tuple(math.log(b['close']/a['close']) for a,b in zip(bars,bars[1:]))
    result=estimate(returns,config)
    starts={t for b in bars for t in b['inputs']}
    return dict(**result,decision_time=time.isoformat(),config=asdict(config),returns=returns,bars=bars,
                market_inputs=[asdict(r) for r in known if r.start.isoformat() in starts],
                available_at=max(b['available_at'] for b in bars))
