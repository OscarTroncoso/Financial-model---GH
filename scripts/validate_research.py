"""Run existing research suites or honest live-data diagnostics, without orders."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import traceback
from zipfile import ZipFile,ZIP_DEFLATED

SUITES={
    'unit': ['-m','unittest','discover','-s','tests','-v'],
    'insurance': ['-m','portfolio_lab.cli','--config','config/lab.json','--suite'],
    'backtest': ['-m','portfolio_backtest.cli','--output'],
    'equity': ['-m','portfolio_equity.cli','--suite'],
    'views': ['-m','portfolio_factors.systematic_cli','--suite'],
    'fx': ['-m','portfolio_fx.cli','--suite'],
    'risk': ['-m','portfolio_fx_risk.cli','--suite'],
    'regimes': ['-m','portfolio_regimes.cli','--suite'],
    'econometrics': ['-m','portfolio_econometrics.cli','--suite'],
}


def save(path: Path,value: dict) -> None:
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def provenance(output: Path) -> None:
    save(output/'runtime.json',dict(python=platform.python_version(),platform=platform.platform(),
         commit=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'),
         captured_at=datetime.now(timezone.utc).isoformat(),
         packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}))
    with ZipFile(output/'source-snapshot.zip','x',ZIP_DEFLATED) as archive:
        for base,pattern in (('src','*.py'),('config','*.json'),('tests','*.py')):
            for path in sorted(Path(base).rglob(pattern)): archive.write(path,path.as_posix())
        for path in (Path('pyproject.toml'),Path('requirements-data.lock'),Path('scripts/validate_research.py')):
            if path.exists(): archive.write(path,path.as_posix())


def synthetic(name: str,output: Path) -> dict:
    command=[sys.executable]+SUITES[name]+([] if name=='unit' else [str(output/'suite')])
    with (output/'execution.log').open('w',encoding='utf-8') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1100)
    if name=='unit':
        content=(output/'execution.log').read_text(encoding='utf-8')
        match=re.search(r'Ran (\d+) tests? in',content)
        if not match: raise ValueError('Unit-test count missing')
        validation=dict(status='passed',tests=int(match.group(1)))
    else:
        validation=json.loads((output/'suite'/'validation.json').read_text(encoding='utf-8'))
        if not str(validation.get('status','')).lower().startswith('pass'): raise ValueError('Suite did not publish passing validation')
    return dict(status='passed',suite=name,validation=validation,evidence='synthetic_engineering',economic_promotion=False)


def live(output: Path,existing_capture: Path|None=None) -> dict:
    from portfolio_fx.providers import capture,fetch_fred_csv,normalize_fred
    from portfolio_fx.audit import encoded,digest
    from portfolio_fx_risk.workflow import bundle,replay
    from portfolio_econometrics.workflow import bundle as econ_bundle,replay as econ_replay
    result=dict(suite='live',status='failed',source_errors={},proposals=[],forecasts=[],
                evidence='current_snapshot_only',historical_backtest_eligible=False,economic_promotion=False,
                account_assumption=dict(nav_usd=10000.,fx_capital_usd=1000.,illustrative=True))
    path=existing_capture or output/'capture'/'normalized.json'
    if existing_capture is None:
        try: result['capture']=capture(path.parent,30)
        except Exception as error:
            result['source_errors']['capture']=type(error).__name__+': '+str(error)
            # Diagnose FRED independently even if Yahoo prevents combined capture.
            for series,currency in (('DFEDTARU','USD'),('ECBDFR','EUR')):
                try:
                    now=datetime.now(timezone.utc)
                    raw=fetch_fred_csv(series,(now-timedelta(days=44)).date().isoformat())
                    (output/(series+'.csv')).write_text(raw,encoding='utf-8')
                    rows=normalize_fred(raw,series,currency,datetime.now(timezone.utc))
                    result[series]=dict(status='available',observations=len(rows))
                except Exception as fred_error:
                    result['source_errors'][series]=type(fred_error).__name__+': '+str(fred_error)
            return result
    document=json.loads(path.read_text(encoding='utf-8')); body=document['payload']
    if digest(body)!=document['checksum']: raise ValueError('Capture checksum mismatch')
    result['source_errors'].update(body['source_errors'])
    result.update(candles=len(body['candles']),rates=len(body['rates']),capture_checksum=document['checksum'],
                  decision_time=body['captured_at'])
    if not body['candles'] or {r['currency'] for r in body['rates']}!={'EUR','USD'}:
        result['source_errors']['coverage']='Missing candles or one policy-rate currency'
    settings=json.loads(Path('config/fx_risk.json').read_text(encoding='utf-8'))
    for model in ('no_trade','trend','mean_reversion','rate_differential'):
        request=dict(candles=body['candles'],rates=body['rates'],time=body['captured_at'],model=model,
                     capacity=dict(nav_usd=10000.,fx_capital_usd=1000.),risk=settings['risk'],
                     volatility=settings['volatility'],config=settings['features'],execution=settings['execution'])
        proposal=bundle(request,'proposal'); proposal_path=output/(model+'-proposal.json')
        proposal_path.write_bytes(encoded(proposal)); replay(proposal_path)
        plan=proposal['payload']['result']['payload']
        if plan['executable']: raise AssertionError('Research proposal unexpectedly executable')
        sized=plan['sizing']
        if sized['state']=='READY' and sized['modeled_stop_loss_usd']>sized['risk_budget_usd']+1e-8:
            raise AssertionError('Research size exceeds modeled risk budget')
        result['proposals'].append(dict(model=model,state=sized['state'],reason=sized.get('reason'),replay='verified'))
    settings=json.loads(Path('config/econometrics.json').read_text(encoding='utf-8'))
    for model in ('no_change','momentum','ar','arimax','var','kalman','markov_switching','vecm'):
        request=dict(candles=body['candles'],rates=body['rates'],time=body['captured_at'],model=model,econometrics=settings)
        prediction=econ_bundle(request,'forecast'); forecast_path=output/(model+'-forecast.json')
        forecast_path.write_bytes(encoded(prediction)); econ_replay(forecast_path)
        forecast=prediction['payload']['result']['payload']
        result['forecasts'].append(dict(model=model,status=forecast['status'],reason=forecast['reason'],replay='verified'))
    result['status']='passed' if not result['source_errors'] else 'failed'
    result['interpretation']='Successful capture/replay does not imply trading readiness; stale inputs and unavailable historical macro vintages may abstain.'
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',required=True,choices=tuple(SUITES)+('live',))
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--existing-capture',type=Path,help='Replay an existing capture offline; never called a fresh download')
    args=parser.parse_args()
    if args.existing_capture and args.suite!='live': parser.error('--existing-capture requires live diagnostics')
    args.output.mkdir(parents=True,exist_ok=False)
    result=dict(status='failed',suite=args.suite)
    try:
        provenance(args.output)
        result=live(args.output,args.existing_capture) if args.suite=='live' else synthetic(args.suite,args.output)
        if args.existing_capture: result['evidence']='existing_snapshot_replay_not_new_download'
    except Exception as error:
        result['error']=type(error).__name__+': '+str(error)
        (args.output/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        save(args.output/'result.json',result)
        text='# '+args.suite+' validation\n\n```json\n'+json.dumps(result,indent=2,allow_nan=False)+'\n```\n'
        (args.output/'summary.md').write_text(text,encoding='utf-8')
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a',encoding='utf-8') as stream: stream.write(text)
        print(json.dumps(result,indent=2,allow_nan=False),flush=True)
    return 0 if result['status']=='passed' else 1

if __name__=='__main__': raise SystemExit(main())
