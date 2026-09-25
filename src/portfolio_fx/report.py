"""Fixed-rule chronological holdouts, cost sensitivity and exact replay."""
from dataclasses import asdict, replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import math
import platform
from .contracts import Candle,Rate,FXConfig,ExecutionConfig
from .engine import run
from .metrics import summarize
from .audit import encoded,digest,source_hash
from .signals import MODELS


def bundle(request: dict) -> dict:
    if set(request)!={'candles','rates','model','start','end','config','execution'}: raise ValueError('Unexpected FX request schema')
    result=run(tuple(Candle(**r) for r in request['candles']),tuple(Rate(**r) for r in request['rates']),
               request['model'],request['start'],request['end'],FXConfig(**request['config']),ExecutionConfig(**request['execution']))
    body=dict(request=request,result=result,metrics=summarize(result),source_hash=source_hash(),python=platform.python_version(),schema=1)
    body=json.loads(encoded(body))
    return dict(checksum=digest(body),payload=body)


def replay(path: Path) -> dict:
    saved=json.loads(path.read_text(encoding='utf-8')); body=saved['payload']
    if digest(body)!=saved['checksum'] or body['schema']!=1: raise ValueError('FX bundle integrity failure')
    if bundle(body['request'])!=saved: raise ValueError('FX source/runtime/replay mismatch')
    return {'status':'verified','checksum':saved['checksum']}


def fixture() -> tuple[tuple[Candle,...],tuple[Rate,...]]:
    """25 synthetic weekdays with complete UTC sessions and changing drift."""
    day=datetime(2020,1,6,tzinfo=timezone.utc); rows=[]; rates=[]; price=1.10
    for d in range(25):
        while day.weekday()>=5: day+=timedelta(days=1)
        rates.extend((Rate('EUR',.03+.015*math.sin(d*.45),day,day,day,'synthetic EUR policy proxy'),
                      Rate('USD',.03,day,day,day,'synthetic USD policy proxy')))
        for slot in range(48):
            start=day+timedelta(minutes=30*slot); end=start+timedelta(minutes=30)
            index=d*48+slot
            close=price*(1+.00015*math.sin(index*.019)+.0002*math.cos(index*.11))
            rows.append(Candle(start,end,price,max(price,close)*1.0001,min(price,close)*.9999,close,end,end,'synthetic EURUSD v1','EURUSD','mid'))
            price=close
        day+=timedelta(days=1)
    return tuple(rows),tuple(rates)


def suite(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=False)
    rows,rates=fixture(); records=[]
    for fold,(first,last) in enumerate(((8,12),(12,16),(16,20)),1):
        for model in MODELS:
            for profile in (('base','high_cost') if model=='trend' else ('base',)):
                settings=ExecutionConfig()
                if profile=='high_cost': settings=replace(settings,commission_bps=5,half_spread_bps=5,slippage_bps=5)
                request=dict(candles=[asdict(r) for r in rows],rates=[asdict(r) for r in rates],model=model,
                    start=rows[first*48].start,end=rows[last*48-1].end,config=asdict(FXConfig()),execution=asdict(settings))
                saved=bundle(request); path=output/f'fold-{fold}--{model}--{profile}.json'
                path.write_bytes(encoded(saved)); replay(path)
                records.append(dict(fold=fold,model=model,profile=profile,**saved['payload']['metrics']))
    for fold in (1,2,3):
        base=next(r for r in records if r['fold']==fold and r['model']=='trend' and r['profile']=='base')
        high=next(r for r in records if r['fold']==fold and r['profile']=='high_cost')
        if not high['costs']>base['costs'] or not high['net_return']<base['net_return']:
            raise AssertionError('Cost sensitivity did not worsen net performance')
    for model in MODELS[1:]:
        if not any(r['completed_trades'] for r in records if r['model']==model):
            raise AssertionError('Baseline not exercised: '+model)
    lines=['# Phase 6 EUR/USD chronological baseline comparison','',
           'Synthetic engineering evidence; fixed parameters chosen before all folds, no tuning or random split.',
           'Independent holdouts start flat and liquidate at their precommitted final close. USD collateral ledger.',
           '', '| Fold | Rule | Costs | Net return | Max drawdown | Trades | Cost USD | Carry USD |',
           '|---|---|---|---:|---:|---:|---:|---:|']
    for r in records:
        lines.append(f"| {r['fold']} | {r['model']} | {r['profile']} | {r['net_return']:.6f} | {r['maximum_drawdown']:.6f} | {r['completed_trades']} | {r['costs']:.4f} | {r['carry']:.4f} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (output/'metrics.json').write_bytes(encoded(records))
    validation=dict(status='passed',chronological_folds=3,models=list(MODELS),saved_cases=len(records),exact_replays=len(records),
                    source_hash=source_hash(),evidence='synthetic_only',economic_promotion=False)
    (output/'validation.json').write_bytes(encoded(validation)); return validation
