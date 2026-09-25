"""Chronological synthetic engineering acceptance; no economic promotion."""
from dataclasses import asdict,replace
from pathlib import Path
from portfolio_fx.report import fixture
from portfolio_fx.contracts import FXConfig,ExecutionConfig
from portfolio_fx_risk.contracts import RiskConfig,VolatilityConfig
from .contracts import RegimeConfig
from .workflow import bundle,replay
from .audit import encoded,source_hash


def suite(output: Path):
    output.mkdir(parents=True,exist_ok=False); rows,rates=fixture(); summaries=[]
    for fold,(first,last) in enumerate(((12,16),(16,20),(20,24)),1):
        for model,profile in [('no_trade','base'),('trend','base'),('mean_reversion','base'),('rate_differential','base'),('trend','high_cost')]:
            execution=ExecutionConfig()
            if profile=='high_cost': execution=replace(execution,commission_bps=5,half_spread_bps=5,slippage_bps=5)
            cutoff=rows[first*48-1].end
            risk_request=dict(candles=[asdict(r) for r in rows],rates=[asdict(r) for r in rates],model=model,
                start=rows[first*48].start,end=rows[last*48-1].end,config=asdict(FXConfig()),execution=asdict(execution),
                risk=asdict(RiskConfig()),volatility=asdict(VolatilityConfig()),fx_capital_fraction=.1)
            request=dict(risk_request=risk_request,training_cutoff=cutoff,config=asdict(RegimeConfig()))
            document=bundle(request,'evaluation'); path=output/f'fold-{fold}--{model}--{profile}.json'
            path.write_bytes(encoded(document)); replay(path)
            body=document['payload']; records=body['records']
            if any(r['payload'][m]['status']!='READY' for r in records for m in ('rule','hmm')):
                raise AssertionError('Acceptance fixture contains unavailable regime')
            summaries.append(dict(fold=fold,model=model,profile=profile,decisions=len(records),
                                  performance=body['performance'],risk_metrics=body['risk_run']['payload']['metrics']))
    validation=dict(status='passed',chronological_folds=3,cases=len(summaries),exact_replays=len(summaries),
                    source_hash=source_hash(),evidence='synthetic_only',economic_promotion=False,risk_limits_unchanged=True)
    (output/'validation.json').write_bytes(encoded(validation)); (output/'metrics.json').write_bytes(encoded(summaries))
    lines=['# Phase 8: entry-decision regime attribution','',
           'Synthetic chronological holdouts; trade P&L includes costs and carry. Safe income is separate.',
           'Conditional trade groups, not independently investable portfolios. No profitability claim.','',
           '| Fold | Model | Cost | Method | State | Trades | Net P&L USD | Costs USD |',
           '|---|---|---|---|---|---:|---:|---:|']
    for case in summaries:
        for method,performance in case['performance'].items():
            for state,g in performance['groups'].items():
                lines.append(f"| {case['fold']} | {case['model']} | {case['profile']} | {method} | {state} | {g['trades']} | {g['net_pnl_usd']:.4f} | {g['costs_usd']:.4f} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return validation
