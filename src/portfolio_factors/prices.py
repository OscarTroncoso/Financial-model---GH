"""Price-only baseline descriptors built from explicit phase-2 vintages."""
from dataclasses import asdict,dataclass
from datetime import datetime
import math
import numpy as np
from portfolio_data.contracts import Datum,utc,validate_series,ensure_fresh
from portfolio_equity.contracts import Universe
from .core import Feature,digest


@dataclass(frozen=True)
class PriceFactorConfig:
    momentum_lookback: int = 252
    momentum_skip: int = 21
    volatility_window: int = 63
    periods_per_year: int = 252
    max_gap_days: int = 7
    max_age_days: int = 7

    def __post_init__(self) -> None:
        for name,value in asdict(self).items():
            if type(value) is not int or value<0: raise ValueError('Nonnegative integer price settings required')
        if not 0<=self.momentum_skip<self.momentum_lookback or self.volatility_window<2:
            raise ValueError('Invalid momentum/volatility window')
        if min(self.periods_per_year,self.max_gap_days,self.max_age_days)<1:
            raise ValueError('Positive annualization and freshness bounds required')


def price_features(universe: Universe,series: dict[str,list[Datum]],decision_time: datetime,
                   config: PriceFactorConfig=PriceFactorConfig()) -> tuple[tuple[Feature,...],dict]:
    """Momentum=P[t-skip]/P[t-lookback]-1; vol=sample std(simple returns)*sqrt(A).

    Daily session-count momentum is a declared proxy, not an exact replication
    of French's calendar-month 2-12 factor portfolios. No size sort is implied.
    Derived timestamps denote calculation at t using only raw vintages known
    then, not retroactive ingestion of vendor observations.
    """
    time=utc(decision_time)
    if universe.available_at>time or set(series)!=set(universe.asset_ids):
        raise ValueError('Unavailable or mismatched universe')
    required=max(config.momentum_lookback,config.volatility_window)+1
    selected={}; calendar=None
    for asset in universe.asset_ids:
        eligible=select_vintages(series[asset],time)
        rows=validate_series(eligible,config.max_gap_days)
        ensure_fresh(rows,time,config.max_age_days)
        if len(rows)<required: raise ValueError('Insufficient available price history')
        rows=rows[-required:]
        if any(r.instrument_id!=asset or r.currency!=universe.currency or r.basis!='adjusted_close' for r in rows):
            raise ValueError('Same-currency adjusted prices with matching asset IDs required')
        dates=[r.observation_time for r in rows]
        if calendar is not None and dates!=calendar: raise ValueError('Unaligned sessions; no forward filling')
        calendar=dates; selected[asset]=rows
    evidence={'decision_time':time.isoformat(),'config':asdict(config),
              'prices':{asset:[r.to_dict() for r in rows] for asset,rows in selected.items()}}
    identifier=digest(evidence); output=[]
    for asset,rows in selected.items():
        prices=np.asarray([r.value for r in rows]); window=prices[-config.volatility_window-1:]
        momentum=float(prices[-1-config.momentum_skip]/prices[-1-config.momentum_lookback]-1)
        volatility=float(np.std(window[1:]/window[:-1]-1,ddof=1)*math.sqrt(config.periods_per_year))
        for factor,value,unit in (('momentum',momentum,'simple_return'),('volatility',volatility,'annual_simple_return_std')):
            output.append(Feature(asset,factor,value,unit,rows[-1].observation_time,time,time,time,
                                  'derived_prices:'+identifier,'price_factor_v1'))
    return tuple(output),{'input_id':identifier,'payload':evidence}


def select_vintages(rows: list[Datum],decision_time: datetime) -> list[Datum]:
    """Latest available revision per observation, filtered BEFORE ranking."""
    time=utc(decision_time); grouped={}
    for row in rows:
        if row.available_to_model_time>time or row.observation_time>time: continue
        grouped.setdefault(row.observation_time,[]).append(row)
    selected=[]
    for stamp,group in sorted(grouped.items()):
        latest=max((r.available_to_model_time,r.ingested_at) for r in group)
        candidates={digest(r.to_dict()):r for r in group if (r.available_to_model_time,r.ingested_at)==latest}
        if len(candidates)!=1: raise ValueError('Conflicting price vintages at identical availability')
        selected.append(next(iter(candidates.values())))
    return selected
