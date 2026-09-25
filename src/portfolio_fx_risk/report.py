"""Chronological volatility/risk comparisons and an explicit adverse-gap stress."""
from dataclasses import asdict,replace
from pathlib import Path
import math
from statistics import mean
from portfolio_fx.report import fixture
from portfolio_fx.data import aggregate
from portfolio_fx.contracts import FXConfig,ExecutionConfig
from .contracts import RiskConfig,VolatilityConfig
from .workflow import bundle,replay
from .audit import encoded,source_hash


def forecast_scores(result: dict,rows) -> dict:
    """Attach subsequent squared-return proxies only AFTER generating the run."""
    bars=aggregate(rows,240); pairs={a['end']:(a,b) for a,b in zip(bars,bars[1:])}
    scores=[]
    for plan in result['signals']:
        vol=plan['payload']['volatility']
        if not vol: continue
        pair=pairs.get(vol['bars'][-1]['end'])
        if pair is None or pair[1]['end']>result['end']: continue
        realized=math.log(pair[1]['close']/pair[0]['close'])**2
        variance=vol['variance']
        scores.append(dict(decision_time=plan['payload']['decision_time'],label_end=pair[1]['end'],
                           forecast_variance=variance,squared_return=realized,
                           qlike=math.log(variance)+realized/variance,squared_error=(variance-realized)**2))
    return dict(n=len(scores),qlike=mean(s['qlike'] for s in scores) if scores else None,
                variance_mse=mean(s['squared_error'] for s in scores) if scores else None,observations=scores)


def suite(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=False); rows,rates=fixture(); records=[]; base_for_stress=None
    cases=[('trend',v,'base') for v in ('realized','ewma','garch')]+[
        ('mean_reversion','realized','base'),('rate_differential','realized','base'),('no_trade','realized','base'),('trend','realized','high_cost')]
    for fold,(first,last) in enumerate(((12,16),(16,20),(20,24)),1):
        for model,vol,profile in cases:
            settings=ExecutionConfig()
            if profile=='high_cost': settings=replace(settings,commission_bps=5,half_spread_bps=5,slippage_bps=5)
            request=dict(candles=[asdict(r) for r in rows],rates=[asdict(r) for r in rates],model=model,
                start=rows[first*48].start,end=rows[last*48-1].end,config=asdict(FXConfig()),execution=asdict(settings),
                risk=asdict(RiskConfig()),volatility=asdict(VolatilityConfig(model=vol)),fx_capital_fraction=.1)
            saved=bundle(request); path=output/f'fold-{fold}--{model}--{vol}--{profile}.json'
            path.write_bytes(encoded(saved)); replay(path)
            result=saved['payload']['result']; scores=forecast_scores(result,rows)
            if not saved['payload']['metrics']['modeled_risk_limits_pass']: raise AssertionError('Risk model exceeded entry budget')
            records.append(dict(fold=fold,model=model,volatility=vol,profile=profile,metrics=saved['payload']['metrics'],forecast_scores=scores))
            if fold==1 and model=='trend' and vol=='realized' and profile=='base': base_for_stress=(request,result)
    request,result=base_for_stress
    trade=next(t for t in result['trades'] if t['holding_hours']>=1)
    index=next(i for i,r in enumerate(rows) if r.start.isoformat()==trade['entry_time'])+1
    shocked=list(rows); factor=1-.03*trade['direction']
    for i in range(index,len(shocked)):
        row=shocked[i]; shocked[i]=replace(row,open=row.open*factor,high=row.high*factor,low=row.low*factor,close=row.close*factor)
    stress_request={**request,'candles':[asdict(r) for r in shocked]}
    stress=bundle(stress_request); path=output/'adverse-gap-stress.json'; path.write_bytes(encoded(stress)); replay(path)
    if not stress['payload']['metrics']['gap_stops'] or not stress['payload']['metrics']['risk_budget_breaches']:
        raise AssertionError('Adverse gap did not exercise unguaranteed stop loss')
    records.append(dict(fold='stress',model='trend',volatility='realized',profile='3_percent_adverse_gap',metrics=stress['payload']['metrics']))
    lines=['# Phase 7 volatility and risk comparison','',
           'Synthetic chronological holdouts; costs/carry included. Forecast QLIKE uses subsequent squared returns, a noisy proxy.',
           'Gap stress deliberately shows that stop orders do not guarantee the modeled budget.','',
           '| Fold | Rule | Volatility | Profile | Net return | Trades | Cost USD | Budget breaches |',
           '|---|---|---|---|---:|---:|---:|---:|']
    for r in records:
        m=r['metrics']; lines.append(f"| {r['fold']} | {r['model']} | {r['volatility']} | {r['profile']} | {m['net_return']:.6f} | {m['completed_trades']} | {m['costs']:.4f} | {m['risk_budget_breaches']} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (output/'metrics.json').write_bytes(encoded(records))
    validation=dict(status='passed',chronological_folds=3,saved_cases=len(records),exact_replays=len(records),
        source_hash=source_hash(),gap_stress_budget_breaches=stress['payload']['metrics']['risk_budget_breaches'],
        evidence='synthetic_only',economic_promotion=False)
    (output/'validation.json').write_bytes(encoded(validation)); return validation
