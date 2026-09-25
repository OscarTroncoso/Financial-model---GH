"""Complete price-factor -> trained view -> constrained equity allocation path."""
from dataclasses import asdict
from datetime import timedelta
import json
from pathlib import Path
import platform
import numpy as np
from portfolio_data.contracts import Datum,utc
from portfolio_equity.contracts import Universe,EquityConfig
from portfolio_equity.pipeline import allocate,returns_from_prices
from .core import config_from_dict,digest,encoded,snapshot
from .prices import PriceFactorConfig,price_features,select_vintages
from .learning import LearningConfig,label_sample,generate_view


def compute(request: dict,settings: dict) -> dict:
    if set(settings)!={'price_factors','normalization','learning','equity'}:
        raise ValueError('Unknown or missing systematic-view settings')
    if set(request)!={'universe','prices','safe_prices','decision_time','training_times'}:
        raise ValueError('Unknown or missing systematic-view inputs')
    universe=Universe(**request['universe']); time=utc(request['decision_time'])
    price_config=PriceFactorConfig(**settings['price_factors'])
    factors=config_from_dict(settings['normalization']); learning=LearningConfig(**settings['learning'])
    equity=EquityConfig(**settings['equity'])
    if price_config.periods_per_year!=learning.periods_per_year or learning.periods_per_year!=equity.periods_per_year:
        raise ValueError('Inconsistent annualization between factors, labels and BL')
    if {f.factor_id for f in factors.factors}!={'momentum','volatility'}:
        raise ValueError('Price workflow requires exactly momentum and volatility descriptors')
    series={asset:[Datum(**r) for r in rows] for asset,rows in request['prices'].items()}
    raw,audit=price_features(universe,series,time,price_config)
    current=snapshot(universe,raw,time,factors)
    known={asset:select_vintages(rows,time) for asset,rows in series.items()}
    pair=(learning.long_asset,learning.short_asset)
    if not set(pair)<=set(known): raise ValueError('Configured pair absent')
    samples=[]; audits=[audit]
    times=sorted({utc(t) for t in request['training_times'] if utc(t)<time})
    for stamp in times:
        raw,historical_audit=price_features(universe,series,stamp,price_config)
        historical=snapshot(universe,raw,stamp,factors)
        paths={asset:[r for r in known[asset] if r.observation_time>=stamp][:learning.horizon_sessions+1] for asset in pair}
        if any(len(rows)<learning.horizon_sessions+1 for rows in paths.values()): continue
        samples.append(label_sample(historical,paths,learning)); audits.append(historical_audit)
    safe=select_vintages([Datum(**r) for r in request['safe_prices']],time)
    returns=returns_from_prices(universe,known,safe,price_config.max_gap_days)
    baseline=allocate(universe,returns,(),time,equity)
    view,model=generate_view(current,tuple(samples),np.asarray(baseline['covariance']['matrix']),equity.tau,learning)
    allocation=allocate(universe,returns,(view,) if view else (),time,equity)
    if view and not np.isclose(allocation['Omega'][0][0],model['effective_omega'],rtol=1e-10,atol=1e-15):
        raise ArithmeticError('BL confidence conversion did not preserve effective Omega')
    return {'snapshot':current,'price_input_audits':audits,'training_samples':samples,
            'model':model,'view':asdict(view) if view else None,'baseline_allocation':baseline,
            'allocation':allocation,'purpose':'research_baseline_not_live_execution'}


def bundle(request: dict,settings: dict) -> dict:
    payload={'schema':1,'request':request,'settings':settings,'result':compute(request,settings),
             'runtime':{'python':platform.python_version(),'numpy':np.__version__}}
    payload=json.loads(encoded(payload))
    return {'checksum':digest(payload),'payload':payload}


def replay(path: Path) -> dict:
    saved=json.loads(path.read_text(encoding='utf-8')); payload=saved['payload']
    if payload['schema']!=1 or digest(payload)!=saved['checksum']: raise ValueError('Bundle integrity failure')
    if bundle(payload['request'],payload['settings'])!=saved: raise ValueError('Code/runtime/result mismatch')
    return {'status':'verified','snapshot_id':payload['result']['snapshot']['snapshot_id']}
