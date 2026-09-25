"""Transparent fixed-rule baselines; no fitted trading probabilities."""
from dataclasses import asdict
from statistics import mean, pstdev
from .contracts import Candle, Rate, FXConfig
from .data import NotReady, aligned, rates_asof, candles_asof
from portfolio_data.contracts import utc
from .audit import digest, source_hash, encoded

MODELS=('no_trade','trend','mean_reversion','rate_differential')


def descriptors(closes: list[float], config: FXConfig) -> dict:
    """SMA trend ratio, fractional ROC and population price z-score (not returns)."""
    import math
    if len(closes)<max(config.slow_window,config.mean_window) or any(not math.isfinite(p) or p<=0 for p in closes):
        raise ValueError('Insufficient/invalid price window')
    slow=mean(closes[-config.slow_window:]); fast=mean(closes[-config.fast_window:])
    window=closes[-config.mean_window:]; center=mean(window); deviation=pstdev(window)
    return dict(fast_sma=fast,slow_sma=slow,trend=fast/slow-1,
                momentum=closes[-1]/closes[-config.slow_window]-1,
                mean=center,price_std=deviation,z=(closes[-1]-center)/deviation if deviation else 0.)


def signal(rows: tuple[Candle,...], rates: tuple[Rate,...], time, model: str, config: FXConfig=FXConfig()) -> dict:
    if model not in MODELS: raise ValueError('Unknown baseline')
    time=utc(time); direction=0; reference=None; features={}; inputs=[]; rate_inputs=[]; clock=None
    try:
        frames,known=aligned(rows,time,config)
        history=frames['4H'][-max(config.slow_window,config.mean_window):]
        features=descriptors([r['close'] for r in history],config)
        features['alignment']={name:values[-1] for name,values in frames.items()}
        features['context_return']={name:values[-1]['close']/values[-2]['close']-1 if len(values)>1 else None for name,values in frames.items()}
        starts={start for row in history for start in row['inputs']}
        for values in frames.values():
            for value in values[-2:]: starts.update(value['inputs'])
        inputs=[asdict(r) for r in known if r.start.isoformat() in starts]
        reference=frames['30m'][-1]['close']; clock=frames['4H'][-1]['end']
        if model=='trend':
            value=features['trend']; direction=1 if value>config.trend_threshold else -1 if value< -config.trend_threshold else 0
        elif model=='mean_reversion':
            value=features['z']; direction=-1 if value>config.reversion_z else 1 if value< -config.reversion_z else 0
        elif model=='rate_differential':
            euro,dollar=rates_asof(rates,time,config.max_rate_age_days)
            rate_inputs=[asdict(euro),asdict(dollar)]; value=euro.value-dollar.value
            features['policy_rate_differential']=value
            direction=1 if value>config.rate_threshold else -1 if value< -config.rate_threshold else 0
        reason='rule_threshold' if direction else 'neutral_or_no_trade_benchmark'
    except NotReady as error:
        reason=str(error)
        inputs=[asdict(r) for r in candles_asof(rows,time)]
        rate_inputs=[asdict(r) for r in rates if r.available_at<=time]
    plan=dict(pair='EURUSD',decision_time=time.isoformat(),model=model,config=asdict(config),source_hash=source_hash(),
              model_version='fx_baseline_v1',regime=None,volatility_forecast=None,
              state='LONG' if direction>0 else 'SHORT' if direction<0 else 'NO_TRADE',direction=direction,
              reason=reason,features=features,market_inputs=inputs,rate_inputs=rate_inputs,primary_close=clock,
              entry_reference=reference,entry_policy='first_observed_open_strictly_after_decision',
              stop=None,take_profit=None,position_size=None,expected_risk=None,confidence=None,
              executable=False,risk_status='phase7_risk_sizing_required')
    return {'signal_id':digest(plan),'payload':plan}


def replay_signal(document: dict) -> dict:
    """Reconstruct a ready or NO_TRADE proposal from its saved evidence."""
    body=document['payload']
    if digest(body)!=document['signal_id']: raise ValueError('Signal checksum mismatch')
    rebuilt=signal(tuple(Candle(**r) for r in body['market_inputs']),tuple(Rate(**r) for r in body['rate_inputs']),
                   body['decision_time'],body['model'],FXConfig(**body['config']))
    if encoded(rebuilt)!=encoded(document): raise ValueError('Signal source/evidence mismatch')
    return {'status':'verified','signal_id':document['signal_id']}
