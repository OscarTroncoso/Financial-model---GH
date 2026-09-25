"""Chronological OLS baseline mapping factor-score spreads to one BL view."""
from dataclasses import asdict,dataclass
from datetime import datetime,timedelta
import math
import numpy as np
from portfolio_data.contracts import Datum,utc,validate_series
from portfolio_equity.contracts import Universe,View
from portfolio_equity.math import covariance,positive
from .core import Feature,config_from_dict,digest,snapshot


@dataclass(frozen=True)
class LearningConfig:
    long_asset: str
    short_asset: str
    horizon_sessions: int = 21
    periods_per_year: int = 252
    minimum_training: int = 20
    maximum_training: int = 120
    embargo_days: int = 1
    maximum_training_age_days: int = 3650
    maximum_recent_label_age_days: int = 90
    max_gap_days: int = 7
    max_confidence: float = .75
    annual_mean_se_floor: float = .001
    max_abs_annual_view: float = .2

    def __post_init__(self) -> None:
        if not self.long_asset or not self.short_asset or self.long_asset==self.short_asset:
            raise ValueError('Distinct fixed pair IDs required')
        for name in ('horizon_sessions','periods_per_year','minimum_training','maximum_training','maximum_training_age_days','maximum_recent_label_age_days','max_gap_days'):
            if type(getattr(self,name)) is not int or getattr(self,name)<1: raise ValueError('Positive integer learning settings required')
        if type(self.embargo_days) is not int or self.embargo_days<0 or not 3<=self.minimum_training<=self.maximum_training:
            raise ValueError('Invalid training/embargo bounds')
        if isinstance(self.max_confidence,bool) or not math.isfinite(self.max_confidence) or not 0<self.max_confidence<1:
            raise ValueError('Confidence cap must be in (0,1)')
        positive(self.annual_mean_se_floor); positive(self.max_abs_annual_view)


def validate_snapshot(document: dict) -> dict:
    """Recompute scores from audited raw feature vintages, not a trusted score field."""
    payload=document['payload']
    if document['snapshot_id']!=digest(payload): raise ValueError('Snapshot checksum mismatch')
    features=tuple(Feature(**{k:v for k,v in record.items() if k!='input_id'}) for record in payload['selected_inputs'])
    rebuilt=snapshot(Universe(**payload['universe']),features,payload['decision_time'],config_from_dict(payload['config']))
    if rebuilt!=document: raise ValueError('Snapshot score/source mismatch')
    return payload


def label_sample(scores: dict,paths: dict[str,list[Datum]],config: LearningConfig) -> dict:
    """Attach a realized nonannual spread label with complete price evidence.

    Label data are future outcomes, never inputs to the feature snapshot.
    Both legs use the same start/end sessions and account currency. The common
    safe benchmark cancels in this relative simple-return difference.
    """
    payload=validate_snapshot(scores); time=utc(payload['decision_time'])
    pair=(config.long_asset,config.short_asset)
    if set(paths)!=set(pair) or not set(pair)<=set(payload['universe']['asset_ids']):
        raise ValueError('Label pair/universe mismatch')
    series=[validate_series(paths[asset],config.max_gap_days) for asset in pair]
    stamps=[r.observation_time for r in series[0]]
    if len(stamps)!=config.horizon_sessions+1 or stamps[0]<time or (stamps[0]-time).total_seconds()>config.max_gap_days*86400:
        raise ValueError('Label horizon/start does not match forecast contract')
    for asset,rows in zip(pair,series):
        if [r.observation_time for r in rows]!=stamps: raise ValueError('Label sessions do not align')
        if any(r.instrument_id!=asset or r.currency!=payload['universe']['currency'] or r.basis!='adjusted_close' for r in rows):
            raise ValueError('Label price identity/currency/basis mismatch')
    value=(series[0][-1].value/series[0][0].value-1)-(series[1][-1].value/series[1][0].value-1)
    available=max(r.available_to_model_time for rows in series for r in rows)
    body={'snapshot':scores,'pair':list(pair),'horizon_sessions':config.horizon_sessions,
          'start_time':stamps[0].isoformat(),'end_time':stamps[-1].isoformat(),
          'available_at':available.isoformat(),'period_spread_return':value,
          'paths':{asset:[r.to_dict() for r in rows] for asset,rows in zip(pair,series)}}
    return {'sample_id':digest(body),'payload':body}


def validate_sample(document: dict,config: LearningConfig) -> dict:
    payload=document['payload']
    if document['sample_id']!=digest(payload): raise ValueError('Training sample checksum mismatch')
    rebuilt=label_sample(payload['snapshot'],{asset:[Datum(**r) for r in rows] for asset,rows in payload['paths'].items()},config)
    if rebuilt!=document: raise ValueError('Training label/evidence mismatch')
    return payload


def ols(x: np.ndarray,y: np.ndarray,x0: float) -> dict:
    """Intercept/slope least squares and variance of the estimated conditional mean.

    Assumes linearity, independent homoskedastic errors and fixed predictors.
    sigma2=SSE/(n-2); Var(mean(x0))=sigma2*(1/n+(x0-xbar)^2/Sxx).
    This is NOT the prediction variance of a future realized return (which
    would add sigma2), nor an empirically calibrated trading probability.
    """
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    if x.ndim!=1 or y.shape!=x.shape or len(x)<3 or not np.isfinite(x).all() or not np.isfinite(y).all() or not math.isfinite(x0):
        raise ValueError('Invalid regression observations')
    mean_x=float(x.mean()); mean_y=float(y.mean()); centered=x-mean_x
    sxx=float(centered@centered)
    if sxx<=1e-12: raise ValueError('Insufficient score variation')
    slope=float(centered@(y-mean_y)/sxx); intercept=mean_y-slope*mean_x
    residuals=y-intercept-slope*x; residual_variance=float(residuals@residuals/(len(x)-2))
    prediction=intercept+slope*x0
    variance=residual_variance*(1/len(x)+(x0-mean_x)**2/sxx)
    result={'intercept':intercept,'slope':slope,'residual_variance':residual_variance,
            'prediction':prediction,'mean_variance':variance,'training_mean':mean_y,
            'score_min':float(x.min()),'score_max':float(x.max()),'n':len(x)}
    if not all(math.isfinite(v) for v in result.values()): raise ValueError('Regression overflow')
    return result


def generate_view(current: dict,samples: tuple[dict,...],risk: np.ndarray,tau: float,
                  config: LearningConfig) -> tuple[View|None,dict]:
    """Fit only fully known labels, purge overlap, embargo, then predict one pair.

    A single fixed-pair view avoids asserting independence between multiple
    predictions sharing fitted coefficients. Zero information -> no view.
    OLS mean variance is used as an explicit plug-in Omega proxy; caps/floors
    are project risk controls, not empirically established confidence levels.
    """
    payload=validate_snapshot(current); time=utc(payload['decision_time'])
    assets=payload['universe']['asset_ids']; pair=(config.long_asset,config.short_asset)
    if not set(pair)<=set(assets): raise ValueError('Configured pair absent from universe')
    sigma=covariance(risk)
    if sigma.shape!=(len(assets),len(assets)): raise ValueError('Risk/universe dimension mismatch')
    positive(tau)
    cutoff=time-timedelta(days=config.embargo_days)
    eligible={}
    for sample in samples:
        # Reconstruct rather than trusting a claimed label availability timestamp.
        row=validate_sample(sample,config)
        start=utc(row['start_time']); end=utc(row['end_time'])
        if utc(row['available_at'])>time or end>cutoff: continue
        if (time-end).total_seconds()>config.maximum_training_age_days*86400: continue
        old=row['snapshot']['payload']
        if old['config']!=payload['config'] or old['universe']['asset_ids']!=assets or old['universe']['currency']!=payload['universe']['currency']:
            raise ValueError('Training factor definition/universe drift; rebuild a consistent experiment')
        if start in eligible and eligible[start]['sample_id']!=sample['sample_id']:
            raise ValueError('Conflicting training samples for the same period')
        eligible[start]=sample
    chosen=[]; boundary=cutoff
    for start,sample in sorted(eligible.items(),reverse=True):
        if utc(sample['payload']['end_time'])<=boundary:
            chosen.append(sample); boundary=start
            if len(chosen)==config.maximum_training: break
    chosen.reverse()
    audit={'decision_time':time.isoformat(),'snapshot_id':current['snapshot_id'],'config':asdict(config),
           'training_sample_ids':[s['sample_id'] for s in chosen],
           'training_available_times':[s['payload']['available_at'] for s in chosen],
           'tau':tau,'risk':sigma.tolist(),'status':'no_view'}
    if len(chosen)<config.minimum_training:
        return None,{**audit,'reason':'insufficient_nonoverlapping_labels'}
    if (time-utc(chosen[-1]['payload']['end_time'])).total_seconds()>config.maximum_recent_label_age_days*86400:
        return None,{**audit,'reason':'stale_training_labels'}
    def spread(s): return s['composite_scores'][pair[0]]-s['composite_scores'][pair[1]]
    x=np.asarray([spread(s['payload']['snapshot']['payload']) for s in chosen]); y=np.asarray([s['payload']['period_spread_return'] for s in chosen])
    x0=spread(payload)
    if float(np.ptp(x))<1e-6: return None,{**audit,'reason':'constant_training_scores'}
    if x0<float(x.min())-1e-12 or x0>float(x.max())+1e-12:
        return None,{**audit,'reason':'score_extrapolation'}
    fitted=ols(x,y,x0); scale=config.periods_per_year/config.horizon_sessions
    q=fitted['prediction']*scale
    if abs(q)>config.max_abs_annual_view:
        return None,{**audit,'fit':fitted,'reason':'forecast_outside_risk_bounds'}
    omega=max(fitted['mean_variance']*scale**2,config.annual_mean_se_floor**2)
    pick=np.zeros(len(assets)); pick[assets.index(pair[0])]=1; pick[assets.index(pair[1])]=-1
    prior_variance=float(tau*pick@sigma@pick)
    confidence=min(config.max_confidence,prior_variance/(prior_variance+omega))
    effective=prior_variance*(1-confidence)/confidence
    audit.update({'status':'ready','fit':fitted,'current_score_spread':x0,'annualization_scale':scale,
                  'annual_excess_spread':q,'raw_mean_variance':fitted['mean_variance']*scale**2,
                  'effective_omega':effective,'confidence':confidence,'P':pick.tolist()})
    model_id=digest(audit)
    return View('systematic_relative_'+pair[0]+'_'+pair[1],tuple(pick),q,confidence,time,'factor_ols:'+model_id),{**audit,'model_id':model_id}
