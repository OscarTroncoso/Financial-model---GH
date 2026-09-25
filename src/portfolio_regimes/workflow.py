"""Self-contained saved requests, inference and cost-inclusive evaluation."""
import json,platform
from pathlib import Path
import numpy as np
from portfolio_fx.contracts import Candle
from portfolio_fx_risk.workflow import bundle as risk_bundle
from portfolio_data.contracts import utc
from .contracts import RegimeConfig
from .engine import infer
from .performance import attribute
from .audit import encoded,digest,source_hash


def bundle(request,kind='inference'):
    expected={'candles','times','training_cutoff','config'} if kind=='inference' else {'risk_request','training_cutoff','config'}
    if kind not in ('inference','evaluation') or set(request)!=expected: raise ValueError('Invalid regime request')
    config=RegimeConfig(**request['config'])
    if kind=='evaluation':
        if utc(request['training_cutoff'])>utc(request['risk_request']['start']): raise ValueError('Training overlaps holdout')
        risk=risk_bundle(request['risk_request'])
        result=risk['payload']['result']; rows=tuple(Candle(**r) for r in request['risk_request']['candles'])
        times=[p['payload']['decision_time'] for p in result['signals']]
    else:
        risk=None; rows=tuple(Candle(**r) for r in request['candles']); times=request['times']
    times=[utc(t) for t in times]
    if not times or times!=sorted(set(times)): raise ValueError('Decision times must be nonempty, ordered and unique')
    records=[infer(rows,t,request['training_cutoff'],config) for t in times]
    performance={m:attribute(result,records,m) for m in ('rule','hmm')} if risk else None
    body=json.loads(encoded(dict(schema=1,kind=kind,request=request,records=records,risk_run=risk,
        performance=performance,source_hash=source_hash(),python=platform.python_version(),numpy=np.__version__)))
    return dict(checksum=digest(body),payload=body)


def replay(path: Path):
    saved=json.loads(path.read_text(encoding='utf-8')); body=saved['payload']
    if body['schema']!=1 or digest(body)!=saved['checksum']: raise ValueError('Regime bundle integrity failure')
    if bundle(body['request'],body['kind'])!=saved: raise ValueError('Regime replay source/runtime/input mismatch')
    return dict(status='verified',checksum=saved['checksum'])
