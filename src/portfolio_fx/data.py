"""As-of revision selection and complete UTC multi-timeframe aggregation."""
from dataclasses import asdict
from datetime import timedelta
from .contracts import Candle, Rate, FXConfig
from portfolio_data.contracts import utc


class NotReady(ValueError):
    """Valid data, but insufficient or stale information: NO_TRADE."""


def candles_asof(rows: tuple[Candle,...], time) -> tuple[Candle,...]:
    time=utc(time); chosen={}
    for row in rows:
        if row.available_at>time or row.end>time: continue
        old=chosen.get(row.start)
        if old is None or (row.available_at,row.ingested_at)>(old.available_at,old.ingested_at): chosen[row.start]=row
        elif (row.available_at,row.ingested_at)==(old.available_at,old.ingested_at) and row!=old:
            raise ValueError('Conflicting candle vintages')
    selected=tuple(chosen[t] for t in sorted(chosen))
    if len({r.quote_basis for r in selected})>1: raise ValueError('Mixed quote bases')
    return selected


def aggregate(rows: tuple[Candle,...], minutes: int) -> list[dict]:
    """Only exact complete UTC buckets; missing/partial sessions never filled.

    Daily is UTC midnight-to-midnight, not a New York 5pm broker candle.
    Availability is the maximum input availability; lineage stores all starts.
    Input must already have one vintage per start.
    """
    if minutes not in (30,60,240,1440): raise ValueError('Unsupported timeframe')
    if len({r.start for r in rows})!=len(rows): raise ValueError('Select vintages before resampling')
    groups={}
    for row in rows:
        midnight=row.start.replace(hour=0,minute=0,second=0,microsecond=0)
        start=midnight+timedelta(minutes=((row.start.hour*60+row.start.minute)//minutes)*minutes)
        groups.setdefault(start,[]).append(row)
    result=[]
    for start,items in sorted(groups.items()):
        items=sorted(items,key=lambda r:r.start)
        if len(items)!=minutes//30 or any(r.start!=start+timedelta(minutes=30*i) for i,r in enumerate(items)): continue
        result.append(dict(start=start.isoformat(),end=(start+timedelta(minutes=minutes)).isoformat(),
            open=items[0].open,high=max(r.high for r in items),low=min(r.low for r in items),close=items[-1].close,
            available_at=max(r.available_at for r in items).isoformat(),inputs=[r.start.isoformat() for r in items]))
    return result


def aligned(rows: tuple[Candle,...], time, config: FXConfig) -> tuple[dict,tuple[Candle,...]]:
    time=utc(time); known=candles_asof(rows,time); result={}
    for name,minutes,age in (('30m',30,config.max_30m_age_minutes),('1H',60,config.max_1h_age_minutes),
                            ('4H',240,config.max_4h_age_minutes),('D',1440,config.max_daily_age_minutes)):
        values=aggregate(known,minutes)
        if not values or (time-utc(values[-1]['end'])).total_seconds()>age*60: raise NotReady('missing_or_stale_'+name)
        result[name]=values
    history=result['4H'][-max(config.slow_window,config.mean_window):]
    if len(history)<max(config.slow_window,config.mean_window): raise NotReady('insufficient_4H_history')
    if any((utc(b['start'])-utc(a['end'])).total_seconds()>config.max_history_gap_hours*3600 for a,b in zip(history,history[1:])):
        raise NotReady('stale_gap_in_history')
    return result,known


def rates_asof(rows: tuple[Rate,...], time, max_age_days: float) -> tuple[Rate,Rate]:
    time=utc(time); selected=[]
    for currency in ('EUR','USD'):
        eligible=[r for r in rows if r.currency==currency and r.available_at<=time]
        if not eligible: raise NotReady('missing_policy_rate_'+currency)
        key=lambda r:(r.observation_time,r.available_at,r.ingested_at)
        latest=max(eligible,key=key)
        if any(key(r)==key(latest) and r!=latest for r in eligible): raise ValueError('Conflicting policy-rate vintage')
        if (time-latest.observation_time).total_seconds()>max_age_days*86400: raise NotReady('stale_policy_rate_'+currency)
        selected.append(latest)
    return tuple(selected)
