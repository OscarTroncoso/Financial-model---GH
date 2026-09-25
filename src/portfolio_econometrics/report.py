"""Precommitted chronological engineering folds, common costs and controls."""
from collections import Counter
from dataclasses import asdict,replace
from pathlib import Path
from portfolio_fx.report import fixture
from portfolio_fx.contracts import FXConfig,ExecutionConfig
from portfolio_fx_risk.contracts import RiskConfig,VolatilityConfig
from portfolio_regimes.contracts import RegimeConfig
from .contracts import EconometricConfig,MODELS
from .workflow import bundle,replay
from .audit import encoded,source_hash


def suite(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=False); rows,rates=fixture(); records=[]; ready=Counter()
    for fold,(first,last) in enumerate(((12,14),(16,18),(20,22)),1):
        for model,profile in [(m,'base') for m in MODELS if m!='vecm']+[('ar','high_cost')]:
            execution=ExecutionConfig()
            if profile=='high_cost': execution=replace(execution,commission_bps=5,half_spread_bps=5,slippage_bps=5)
            request=dict(candles=[asdict(r) for r in rows],rates=[asdict(r) for r in rates],model=model,
                start=rows[first*48].start,end=rows[last*48-1].end,econometrics=asdict(EconometricConfig()),
                features=asdict(FXConfig()),execution=asdict(execution),risk=asdict(RiskConfig()),
                volatility=asdict(VolatilityConfig()),fx_capital_fraction=.1,regimes=asdict(RegimeConfig()))
            document=bundle(request); path=output/f'fold-{fold}--{model}--{profile}.json'
            path.write_bytes(encoded(document)); replay(path); body=document['payload']; evaluation=body['evaluation']
            if not body['metrics']['modeled_risk_limits_pass']: raise AssertionError('Independent risk limit failed')
            ready[model]+=evaluation['forecast_status_counts'].get('READY',0)
            records.append(dict(fold=fold,model=model,profile=profile,metrics=body['metrics'],
                                evaluation={k:v for k,v in evaluation.items() if k not in ('regimes','observations')}))
    if any(ready[m]==0 for m in MODELS if m!='vecm'): raise AssertionError('A challenger has no valid forecasts in acceptance fixtures')
    validation=dict(status='passed',cases=len(records),exact_replays=len(records),chronological_folds=3,
                    source_hash=source_hash(),ready_forecasts_by_model=dict(ready),vecm='disabled_pending_evidence',
                    evidence='synthetic_only',economic_promotion=False)
    (output/'validation.json').write_bytes(encoded(validation)); (output/'metrics.json').write_bytes(encoded(records))
    lines=['# Phase 9 econometric comparison','',
           'Synthetic rolling refits in chronological holdouts. No tuning on holdouts. USD risk ledger includes fees/spread/slippage/carry/safe income.',
           'ARIMAX is ARX(1); VAR shares that first equation on the same two-variable sample. VECM is disabled.',
           'Conditional prediction errors use available forecasts; paired no-change errors use identical label timestamps.','',
           '| Fold | Model | Costs | Coverage | RMSE | Net return | Trades | Research status |',
           '|---|---|---|---:|---:|---:|---:|---|']
    for record in records:
        e=record['evaluation']; m=record['metrics']; rmse=e['forecast_metrics']['rmse']
        lines.append(f"| {record['fold']} | {record['model']} | {record['profile']} | {e['coverage']:.3f} | {rmse if rmse is not None else 'NA'} | {m['net_return']:.6f} | {m['completed_trades']} | {e['research_status']} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return validation
