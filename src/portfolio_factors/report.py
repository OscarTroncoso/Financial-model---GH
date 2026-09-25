"""Deterministic walk-forward engineering evidence with simple forecast baselines."""
from dataclasses import asdict,replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
from portfolio_data.contracts import Datum
from portfolio_equity.contracts import Universe,EquityConfig
from portfolio_equity.rebalance import Account,schedule,execute
from .core import FactorConfig,FactorSpec,encoded,digest,source_hash
from .prices import PriceFactorConfig
from .learning import LearningConfig,label_sample
from .workflow import bundle,replay


def default_settings(pair: tuple[str,str]=('SYNTH_A','SYNTH_B')) -> dict:
    return {'price_factors':asdict(PriceFactorConfig()),
            'normalization':asdict(FactorConfig((FactorSpec('momentum','simple_return',1,.6,7),
                                                 FactorSpec('volatility','annual_simple_return_std',-1,.4,7)))),
            'learning':asdict(LearningConfig(*pair)), 'equity':asdict(EquityConfig())}


def synthetic_data() -> tuple[dict,dict]:
    """Three synthetic EUR instruments; smaller descriptor/label horizons for a fixture."""
    day=datetime(2020,1,2,16,tzinfo=timezone.utc)
    universe=Universe(('SYNTH_A','SYNTH_B','SYNTH_C'),'EUR',(.4,.35,.25),day,'synthetic fixed universe')
    series={asset:[] for asset in universe.asset_ids}; safe=[]; prices=np.array([100.,110.,90.])
    times=[]
    for i in range(181):
        while day.weekday()>=5: day+=timedelta(days=1)
        if i:
            returns=np.array([.0002+.001*np.sin(i*.17)+.0006*np.cos(i*.53),
                              .00015+.0009*np.cos(i*.21)+.0004*np.sin(i*.43),
                              .0001+.0011*np.sin(i*.13+.7)])
            prices*=1+returns
        for asset,price in zip(universe.asset_ids,prices):
            series[asset].append(Datum(asset,day,float(price),'EUR','adjusted_close','EUR_per_share',day,day).to_dict())
        safe.append(Datum('SAFE',day,100.,'EUR','adjusted_close','EUR_per_share',day,day).to_dict())
        times.append(day); day+=timedelta(days=1)
    settings=default_settings()
    settings['price_factors'].update(momentum_lookback=20,momentum_skip=2,volatility_window=10)
    settings['learning'].update(horizon_sessions=5,max_abs_annual_view=.5)
    request={'universe':asdict(universe),'prices':series,'safe_prices':safe,'decision_time':times[150],
             'training_times':times[20:176:5]}
    return request,settings


def cost_example(allocation: dict,config: EquityConfig) -> dict:
    """A flat delayed execution mark isolates turnover/costs; no trading P&L claim."""
    account=Account((1500,1500,1500),5500,10000,10000)
    time=datetime.fromisoformat(allocation['decision_time'])
    account,plan,decision=schedule(account,tuple(allocation['optimizer']['weights']),time,None,digest(allocation),config,100)
    if plan:
        account,fill=execute(account,plan,time+timedelta(hours=17),config)
        return {'decision':decision,'fill':fill,'final_account':asdict(account)}
    return {'decision':decision,'costs':0.,'final_account':asdict(account)}


def acceptance_suite(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=False)
    request,settings=synthetic_data(); times=[r['observation_time'] for r in request['prices']['SYNTH_A']]
    records=[]; saved=0; valid=0
    lines=['# Phase 5 chronological validation','',
           'Synthetic numerical evidence. Forecast errors are not trading profits; costs below use flat execution marks.','',
           '| Fold | Status | Train n | Annual view | Confidence | Forecast error (period) |',
           '|---|---|---:|---:|---:|---:|']
    for index in (140,145,150,155,160,165):
        selected={**request,'decision_time':times[index]}
        document=bundle(selected,settings)
        path=output/f'fold-{index}.json'; path.write_bytes(encoded(document)); replay(path); saved+=1
        result=document['payload']['result']; model=result['model']
        pair=(settings['learning']['long_asset'],settings['learning']['short_asset'])
        realized=label_sample(result['snapshot'],{asset:[Datum(**r) for r in request['prices'][asset][index:index+6]] for asset in pair},LearningConfig(**settings['learning']))
        truth=realized['payload']['period_spread_return']
        record={'index':index,'decision_time':times[index],'status':model['status'],'realized':realized}
        if result['view']:
            valid+=1; scale=model['annualization_scale']; prediction=result['view']['annual_excess_return']/scale
            record.update(prediction=prediction,error=prediction-truth,zero_baseline_error=-truth,
                          mean_baseline_error=model['fit']['training_mean']-truth)
            lines.append(f"| {index} | ready | {model['fit']['n']} | {result['view']['annual_excess_return']:.6f} | {model['confidence']:.4f} | {prediction-truth:.6f} |")
        else:
            lines.append(f"| {index} | {model['reason']} | {len(model['training_sample_ids'])} | â€” | â€” | â€” |")
        cfg=EquityConfig(**settings['equity'])
        record['model_cost_example']=cost_example(result['allocation'],cfg)
        record['no_view_cost_example']=cost_example(result['baseline_allocation'],cfg)
        record['high_cost_example']=cost_example(result['allocation'],replace(cfg,commission_bps=50,half_spread_bps=20,slippage_bps=20))
        records.append(record)
    if not valid: raise AssertionError('Acceptance suite did not exercise any generated views')
    errors=[r for r in records if 'error' in r]
    metrics={name:float(np.mean([r[key]**2 for r in errors])) for name,key in
             (('ols_period_mse','error'),('zero_period_mse','zero_baseline_error'),('historical_mean_period_mse','mean_baseline_error'))}
    lines+=['','| Fold | No-view costs | Systematic-view costs | High-cost profile |',
            '|---|---:|---:|---:|']
    for record in records:
        costs=[record[key].get('fill',{}).get('costs',0.) for key in ('no_view_cost_example','model_cost_example','high_cost_example')]
        lines.append(f"| {record['index']} | {costs[0]:.6f} | {costs[1]:.6f} | {costs[2]:.6f} |")
    lines+=['',f'Comparable folds: {valid}. Forecast MSE: {metrics}.',
            'No economic promotion: synthetic inputs, OLS assumptions unverified on market data.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (output/'walk-forward.json').write_bytes(encoded({'records':records,'metrics':metrics}))
    validation={'status':'passed','walk_forward_folds':saved,'exact_replays':saved,'generated_views':valid,
                'source_hash':source_hash(),'metrics':metrics,'evidence':'synthetic_only','economic_promotion':False}
    (output/'validation.json').write_bytes(encoded(validation)); return validation
