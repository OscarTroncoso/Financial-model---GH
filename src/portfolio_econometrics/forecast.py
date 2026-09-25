"""One shared as-of forecast interface; rejected fits never become trades."""
from dataclasses import asdict
from datetime import datetime
import math
import numpy as np
from portfolio_data.contracts import utc
from portfolio_fx.contracts import Candle,Rate
from portfolio_fx.data import candles_asof,aggregate,rates_asof,NotReady
from .contracts import EconometricConfig,MODELS,Rejected
from . import linear,kalman,markov
from .audit import digest,source_hash


def forecast(rows: tuple[Candle,...],rates: tuple[Rate,...],time: datetime|str,model: str,
             config: EconometricConfig=EconometricConfig()) -> dict:
    """Rolling refit on exactly window known returns; target is next observed 4H return.

    Macro inputs at each historical bar are the policy rates actually known
    then. Their first differences are model features, never financing costs.
    """
    if model not in MODELS: raise ValueError('Unknown econometric model')
    time=utc(time)
    body=dict(model=model,decision_time=time.isoformat(),model_version='econometrics_v1',config=asdict(config),
              source_hash=source_hash(),target='next_observed_4H_log_return',inputs={},mean=None,variance=None,
              executable=False,parameters=None,diagnostics={})
    try:
        if model=='vecm':
            body.update(status='DISABLED',reason='cointegration_and_economic_rationale_not_established')
        else:
            bars=aggregate(candles_asof(rows,time),240)[-config.window-1:]
            body['inputs']['bars']=bars
            if len(bars)!=config.window+1: raise NotReady('insufficient_training_history')
            if (time-utc(bars[-1]['end'])).total_seconds()>config.maximum_age_minutes*60: raise NotReady('stale_training_data')
            if any((utc(b['start'])-utc(a['end'])).total_seconds()>config.maximum_gap_hours*3600 for a,b in zip(bars,bars[1:])): raise NotReady('training_gap')
            returns=[math.log(b['close']/a['close']) for a,b in zip(bars,bars[1:])]
            body['inputs']['returns']=returns; macro=None
            if model in ('arimax','var'):
                levels=[]; snapshots=[]
                for bar in bars:
                    eur,usd=rates_asof(rates,bar['end'],config.maximum_rate_age_days)
                    levels.append(eur.value-usd.value)
                    snapshots.append(dict(time=bar['end'],eur=asdict(eur),usd=asdict(usd)))
                macro=np.diff(levels).tolist(); body['inputs'].update(macro_changes=macro,rate_snapshots=snapshots)
            if model in ('no_change','momentum'):
                result=dict(mean=0. if model=='no_change' else returns[-1],variance=float(np.var(returns,ddof=1)),
                            parameters={},diagnostics={},variance_kind='sample_return_variance_baseline')
            elif model in ('ar','arimax','var'): result=linear.estimate(returns,macro,model,config)
            elif model=='kalman': result=kalman.estimate(returns,config)
            else: result=markov.estimate(returns,config)
            body.update(result)
            if not math.isfinite(result['mean']) or not math.isfinite(result['variance']) or result['variance']<0: raise Rejected('invalid_forecast_moments')
            if abs(result['mean'])>min(config.maximum_absolute_return,config.maximum_forecast_sigma*max(float(np.std(returns)),config.minimum_scale)):
                raise Rejected('excessive_forecast')
            body.update(status='READY',reason='fit_passed_predefined_checks')
    except NotReady as error: body.update(status='UNAVAILABLE',reason=str(error),mean=None,variance=None)
    except (Rejected,np.linalg.LinAlgError) as error: body.update(status='REJECTED',reason=str(error),mean=None,variance=None)
    return dict(forecast_id=digest(body),payload=body)
