"""Self-contained risk experiments and proposal replay from original inputs."""
from pathlib import Path
import json
import platform
from portfolio_fx.contracts import Candle,Rate,FXConfig,ExecutionConfig
from portfolio_fx.metrics import summarize
from .contracts import Capacity,RiskConfig,VolatilityConfig
from .engine import run
from .plans import propose
from .audit import encoded,digest,source_hash


def bundle(request: dict,kind: str='backtest') -> dict:
    common={'candles','rates','model','config','execution','risk','volatility'}
    expected=common|({'time','capacity'} if kind=='proposal' else {'start','end','fx_capital_fraction'})
    if kind not in ('proposal','backtest') or set(request)!=expected: raise ValueError('Invalid risk request schema')
    rows=tuple(Candle(**r) for r in request['candles']); rates=tuple(Rate(**r) for r in request['rates'])
    features=FXConfig(**request['config']); execution=ExecutionConfig(**request['execution'])
    risk=RiskConfig(**request['risk']); volatility=VolatilityConfig(**request['volatility'])
    if kind=='proposal':
        result=propose(rows,rates,request['time'],request['model'],Capacity(**request['capacity']),risk,volatility,features,execution)
        metrics=None
    else:
        result=run(rows,rates,request['model'],request['start'],request['end'],features,execution,risk,volatility,request['fx_capital_fraction'])
        metrics=summarize(result)
        metrics.update(risk_budget_breaches=sum(t['budget_exceeded'] for t in result['trades']),
                       gap_stops=sum(t['exit_reason']=='gap_stop' for t in result['trades']),
                       modeled_risk_limits_pass=all(t['modeled_stop_loss_usd']<=t['risk_budget_usd']+1e-8 for t in result['trades']))
    body=json.loads(encoded(dict(kind=kind,schema=1,request=request,result=result,metrics=metrics,
                                 python=platform.python_version(),source_hash=source_hash())))
    return dict(checksum=digest(body),payload=body)


def replay(path: Path) -> dict:
    saved=json.loads(path.read_text(encoding='utf-8')); body=saved['payload']
    if body['schema']!=1 or digest(body)!=saved['checksum']: raise ValueError('Risk bundle integrity failure')
    if bundle(body['request'],body['kind'])!=saved: raise ValueError('Risk replay source/runtime/input mismatch')
    return dict(status='verified',checksum=saved['checksum'])
