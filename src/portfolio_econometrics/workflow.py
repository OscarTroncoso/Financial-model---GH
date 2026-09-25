"""Shared chronological evaluation and reproducible forecast/proposal bundles."""
import json,platform
from dataclasses import asdict
from functools import partial
from pathlib import Path
import numpy as np
from portfolio_fx.contracts import Candle,Rate,FXConfig,ExecutionConfig
from portfolio_fx.metrics import summarize
from portfolio_fx_risk.contracts import RiskConfig,VolatilityConfig,Capacity
from portfolio_regimes.contracts import RegimeConfig
from .contracts import EconometricConfig
from .forecast import forecast
from .plans import propose
from .ledger import run
from .evaluation import evaluate
from .audit import encoded,digest,source_hash


def bundle(request: dict,kind: str='evaluation') -> dict:
    common={'candles','rates','model','econometrics'}
    extra={'time'} if kind=='forecast' else {'time','capacity','risk','volatility','features','execution'} if kind=='proposal' else {'start','end','risk','volatility','features','execution','fx_capital_fraction','regimes'}
    if kind not in ('forecast','proposal','evaluation') or set(request)!=common|extra: raise ValueError('Invalid econometric request schema')
    rows=tuple(Candle(**r) for r in request['candles']); rates=tuple(Rate(**r) for r in request['rates']); config=EconometricConfig(**request['econometrics'])
    metrics=None; evaluation=None
    if kind=='forecast': result=forecast(rows,rates,request['time'],request['model'],config)
    else:
        features=FXConfig(**request['features']); execution=ExecutionConfig(**request['execution'])
        risk=RiskConfig(**request['risk']); volatility=VolatilityConfig(**request['volatility'])
        if kind=='proposal': result=propose(rows,rates,request['time'],request['model'],Capacity(**request['capacity']),risk,volatility,features,execution,config)
        else:
            regimes=RegimeConfig(**request['regimes'])
            if regimes.rule_window>config.window: raise ValueError('Regime window exceeds forecast sample')
            result=run(rows,rates,request['model'],request['start'],request['end'],features,execution,risk,volatility,request['fx_capital_fraction'],partial(propose,econometrics=config))
            metrics=summarize(result)
            metrics.update(risk_budget_breaches=sum(t['budget_exceeded'] for t in result['trades']),
                           modeled_risk_limits_pass=all(t['modeled_stop_loss_usd']<=t['risk_budget_usd']+1e-8 for t in result['trades']))
            evaluation=evaluate(result,rows,metrics,config,regimes)
    body=json.loads(encoded(dict(schema=1,kind=kind,request=request,result=result,metrics=metrics,evaluation=evaluation,
                                 source_hash=source_hash(),python=platform.python_version(),numpy=np.__version__)))
    return dict(checksum=digest(body),payload=body)


def replay(path: Path) -> dict:
    saved=json.loads(path.read_text(encoding='utf-8')); body=saved['payload']
    if body['schema']!=1 or digest(body)!=saved['checksum']: raise ValueError('Econometric integrity failure')
    if bundle(body['request'],body['kind'])!=saved: raise ValueError('Econometric replay source/runtime/input mismatch')
    return dict(status='verified',checksum=saved['checksum'])
