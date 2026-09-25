"""Versioned allocation bundles, published-example verification and replay."""
from dataclasses import asdict, replace
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import portfolio_lab
import portfolio_data
from .contracts import EquityConfig,Universe,ReturnRow,View
from .models import posterior
from .pipeline import allocate
from .rebalance import Account,schedule,execute


def encoded(value) -> bytes:
    return json.dumps(value,sort_keys=True,indent=2,allow_nan=False,
                      default=lambda x:x.isoformat()).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def source_hash() -> str:
    paths=list(Path(__file__).parent.rglob('*.py'))+list(Path(__file__).parent.rglob('*.json'))
    paths+=list(Path(portfolio_lab.__file__).parent.glob('*.py'))+list(Path(portfolio_data.__file__).parent.glob('*.py'))
    return digest({str(p.relative_to(p.parent.parent) if p.suffix=='.py' else Path('portfolio_equity')/'fixtures'/p.name):
                   hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})


def run_request(request: dict, config: EquityConfig) -> dict:
    required={'universe','returns','views','decision_time','account','previous_monthly_decision','contribution'}
    if not required <= set(request) or set(request)-required-{'execution'}:
        raise ValueError('Unknown or missing request fields')
    universe=Universe(**request['universe'])
    rows=tuple(ReturnRow(**r) for r in request['returns'])
    views=tuple(View(**v) for v in request['views'])
    allocation=allocate(universe,rows,views,request['decision_time'],config)
    allocation_id=digest(allocation)
    account,plan,decision=schedule(Account(**request['account']),tuple(allocation['optimizer']['weights']),
        request['decision_time'],request['previous_monthly_decision'],allocation_id,config,request['contribution'])
    result={'allocation':allocation,'allocation_id':allocation_id,'decision':decision,
            'account_after_contribution':asdict(account),'plan':asdict(plan) if plan else None}
    if 'execution' in request:
        observed=request['execution']
        if set(observed)!={'time','equity_returns','safe_return'}:
            raise ValueError('Execution mark requires explicit time and all realized returns')
        if not plan:
            result['execution']={'status':'no_order'}
        else:
            account=account.mark(tuple(observed['equity_returns']),observed['safe_return'])
            account,fill=execute(account,plan,observed['time'],config)
            result['execution']=fill
    return result


def bundle(request: dict, config: EquityConfig) -> dict:
    result=run_request(request,config)
    payload={'schema':1,'source_hash':source_hash(),
             'runtime':{'python':platform.python_version(),'numpy':np.__version__},
             'request':request,'config':asdict(config),'result':result}
    payload=json.loads(encoded(payload))
    return {'checksum':digest(payload),'payload':payload}


def replay(path: Path) -> dict:
    document=json.loads(path.read_text(encoding='utf-8')); payload=document['payload']
    if document['checksum']!=digest(payload): raise ValueError('Bundle checksum mismatch')
    if payload['schema']!=1 or payload['source_hash']!=source_hash(): raise ValueError('Source/schema mismatch')
    result=bundle(payload['request'],EquityConfig(**payload['config']))
    if result!=document: raise ValueError('Replay or runtime mismatch')
    return {'status':'verified','allocation_id':payload['result']['allocation_id']}


def published_example() -> dict:
    fixture=json.loads((Path(__file__).parent/'fixtures/idzorek_2004.json').read_text(encoding='utf-8'))
    sigma=np.asarray(fixture['covariance']); picks=np.asarray(fixture['P'])
    omega=np.diag(np.diag(picks@(fixture['tau']*sigma)@picks.T))
    actual=posterior(sigma,fixture['prior'],fixture['tau'],picks,fixture['Q'],omega)
    difference=float(np.max(np.abs(np.asarray(actual.mean)-fixture['published_posterior'])))
    if difference>fixture['rounding_tolerance_mean']: raise AssertionError('Published example failed')
    return {'source':fixture['source'],'actual_mean':actual.mean,'published_mean':fixture['published_posterior'],
            'max_absolute_difference':difference,'tolerance':fixture['rounding_tolerance_mean'],
            'note':'Rounded published inputs; original unconstrained weights are not production targets.'}


def synthetic_request() -> dict:
    start=datetime(2020,1,2,16,tzinfo=timezone.utc)
    rows=[]; day=start
    for i in range(60):
        while day.weekday()>=5: day+=timedelta(days=1)
        values=(.006*np.sin(i*.7)+.002*np.cos(i*.17),.005*np.cos(i*.6)-.002*np.sin(i*.3))
        rows.append(asdict(ReturnRow(day,day,values,'synthetic_daily_excess_fixture')))
        day+=timedelta(days=1)
    time=rows[-1]['observation_time']
    return {'universe':asdict(Universe(('SYNTH_A','SYNTH_B'),'EUR',(.6,.4),start,'chosen synthetic reference, not observed market cap')),
            'returns':rows,'views':[],'decision_time':time,
            'account':asdict(Account((2000,1000),7000,10000,10000)),
            'previous_monthly_decision':None,'contribution':100,
            'execution':{'time':time+timedelta(days=1),'equity_returns':[0,0],'safe_return':0}}


def monthly_example(config: EquityConfig) -> dict:
    """Sequential contribution/decision/next-open ledger with exact replay inputs.

    Synthetic excess history informs each monthly decision. Prices are flat
    between decision and execution in this fixture; no historical backtest claim.
    """
    template=synthetic_request()
    account=Account((0,0),10000,10000,10000)
    previous=None; entries=[]
    for i,row in enumerate(template['returns']):
        if i+1<config.minimum_observations: continue
        time=row['observation_time']
        if previous is not None and (time.year,time.month)==(previous.year,previous.month): continue
        request={**template,'returns':template['returns'][:i+1],'decision_time':time,
                 'account':asdict(account),'previous_monthly_decision':previous,
                 'contribution':0 if previous is None else 100,
                 'execution':{'time':time+timedelta(hours=17),'equity_returns':[0,0],'safe_return':0}}
        result=run_request(request,config)
        account=Account(**(result['execution']['post_account'] if 'post_account' in result['execution'] else result['account_after_contribution']))
        previous=time
        entries.append({'request':request,'result':result})
    return {'entries':entries,'final_account':asdict(account),'note':'Synthetic flat execution marks; not a market-performance backtest.'}


def acceptance_suite(output: Path, config: EquityConfig) -> dict:
    output.mkdir(parents=True,exist_ok=False)
    paper=published_example()
    (output/'published-example.json').write_bytes(encoded(paper))
    lines=['# Phase 4 covariance/view comparison','',
           'Synthetic inputs and flat next-open execution marks; no investment-performance claim.','',
           '| Covariance | View | Weight A | Weight B | Mean A | Mean B | Costs EUR |',
           '|---|---|---:|---:|---:|---:|---:|']
    count=0
    for method in ('sample','ewma','ledoit_wolf'):
        cfg=replace(config,covariance_method=method)
        for label,pick,q,confidence in (('no_views',None,0,0),('absolute_low',(1,0),.08,.25),
                                         ('absolute_high',(1,0),.08,.75),('relative',(1,-1),.01,.5)):
            request=synthetic_request()
            if pick:
                request['views']=[asdict(View(label,pick,q,confidence,request['decision_time'],'synthetic declared opinion'))]
            document=bundle(request,cfg)
            path=output/f'{method}--{label}.json'; path.write_bytes(encoded(document)); replay(path); count+=1
            result=document['payload']['result']; allocation=result['allocation']
            w=allocation['optimizer']['weights']; mu=allocation['posterior']['mean']
            costs=result['execution'].get('costs',0)
            lines.append(f'| {method} | {label} | {w[0]:.6f} | {w[1]:.6f} | {mu[0]:.6f} | {mu[1]:.6f} | {costs:.6f} |')
    monthly=monthly_example(config)
    for index,entry in enumerate(monthly['entries']):
        path=output/f'monthly-{index}.json'; path.write_bytes(encoded(bundle(entry['request'],config))); replay(path)
    (output/'monthly-ledger.json').write_bytes(encoded(monthly))
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    validation={'status':'passed','allocation_cases':count,'monthly_cases':len(monthly['entries']),
                'exact_replays':count+len(monthly['entries']),'published_example':paper,
                'source_hash':source_hash(),'evidence':'synthetic_and_published_numeric_example'}
    (output/'validation.json').write_bytes(encoded(validation))
    return validation
