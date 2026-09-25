"""As-of regime inference, with frozen training vintages and causal labels."""
from dataclasses import asdict
import math
from statistics import stdev
from portfolio_data.contracts import utc
from portfolio_fx.data import aggregate,candles_asof,NotReady
from .contracts import RegimeConfig
from .hmm import fit,filter_returns
from .audit import digest,source_hash

RULE_STATES=tuple(a+'_'+b for a in ('down','sideways','up') for b in ('low','medium','high'))


def rule(returns, config=RegimeConfig()):
    """Project convention: signed path efficiency and sample return volatility.

    Thresholds are research settings, not a published trading model. One-hot
    membership is deterministic, not an empirically calibrated probability.
    """
    if len(returns)!=config.rule_window or not all(math.isfinite(r) for r in returns): raise ValueError('Invalid rule sample')
    denominator=sum(abs(r) for r in returns)
    efficiency=sum(returns)/denominator if denominator else 0.
    sigma=stdev(returns)
    trend='up' if efficiency>=config.trend_threshold else 'down' if efficiency<=-config.trend_threshold else 'sideways'
    vol='low' if sigma<config.low_volatility else 'high' if sigma>=config.high_volatility else 'medium'
    state=trend+'_'+vol
    return dict(state=state,probabilities={s:float(s==state) for s in RULE_STATES},
                probability_kind='deterministic_membership',efficiency=efficiency,sigma=sigma,
                event_context='unavailable',mean_reversion_confirmed=False)


def _check(bars,time,config):
    if not bars or (utc(time)-utc(bars[-1]['end'])).total_seconds()>config.maximum_age_minutes*60: raise NotReady('missing_or_stale_4H')
    if any((utc(b['start'])-utc(a['end'])).total_seconds()>config.maximum_gap_hours*3600 for a,b in zip(bars,bars[1:])):
        raise NotReady('excessive_history_gap')


def _returns(bars):
    return [math.log(b['close']/a['close']) for a,b in zip(bars,bars[1:])]


def infer(rows, time, training_cutoff, config=RegimeConfig()):
    """Infer only using data available by time; fit only by training_cutoff.

    Cutoff must be an earlier UTC four-hour boundary. Training vintages are
    frozen there; subsequent returns bridge from the last frozen close.
    HMM states are relative variance ranks within this fit, not stress labels.
    Missing/stale/degenerate data produce UNKNOWN independently per model.
    """
    time=utc(time); cutoff=utc(training_cutoff)
    if cutoff>=time or cutoff.hour%4 or cutoff.minute or cutoff.second or cutoff.microsecond:
        raise ValueError('Training cutoff must be an earlier UTC 4H boundary')
    known=candles_asof(rows,time); bars=aggregate(known,240)
    train=aggregate(candles_asof(rows,cutoff),240)[-config.training_window-1:]
    body=dict(decision_time=time.isoformat(),training_cutoff=cutoff.isoformat(),version='fx_regimes_v1',
              config=asdict(config),source_hash=source_hash(),executable=False)
    for name in ('rule','hmm'):
        inputs={}
        try:
            if name=='rule':
                sample=bars[-config.rule_window-1:]; inputs=dict(bars=sample)
                _check(sample,time,config)
                if len(sample)!=config.rule_window+1: raise NotReady('insufficient_rule_history')
                result=rule(_returns(sample),config)
            else:
                inputs=dict(training_bars=train)
                _check(train,cutoff,config)
                if len(train)!=config.training_window+1: raise NotReady('insufficient_hmm_training')
                if utc(train[-1]['end'])!=cutoff: raise NotReady('incomplete_training_boundary')
                observations=[b for b in bars if utc(b['end'])>cutoff]
                inputs['filter_bars']=observations
                _check(train[-1:]+observations,time,config)
                if not observations: raise NotReady('no_post_training_observation')
                model=fit(_returns(train),config)
                probabilities,ll=filter_returns(_returns(train[-1:]+observations),model)
                names=['variance_rank_'+str(i) for i in range(config.states)]
                result=dict(state=names[max(range(config.states),key=lambda i:probabilities[-1][i])],
                            probabilities=dict(zip(names,probabilities[-1])),probability_kind='filtered_hmm_posterior',
                            fit=model,filtered_path=[dict(end=b['end'],probabilities=dict(zip(names,prob))) for b,prob in zip(observations,probabilities)],
                            holdout_log_likelihood=ll,event_context='unavailable')
            result.update(status='READY',inputs=inputs)
        except NotReady as error:
            result=dict(status='UNKNOWN',state='UNKNOWN',probabilities={'UNKNOWN':1.},
                        probability_kind='abstention_marker',reason=str(error),inputs=inputs)
        body[name]=result
    return dict(regime_id=digest(body),payload=body)
