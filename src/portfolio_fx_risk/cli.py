"""Research-only FX risk plans, chronological validation and exact replay."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
from portfolio_fx.signals import MODELS
from .contracts import Capacity
from .audit import digest,encoded
from .workflow import bundle,replay
from .report import suite


def main():
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--suite',type=Path); modes.add_argument('--replay',type=Path)
    modes.add_argument('--input',type=Path); modes.add_argument('--capture',type=Path)
    parser.add_argument('--output',type=Path); parser.add_argument('--config',type=Path,default=Path('config/fx_risk.json'))
    parser.add_argument('--model',choices=MODELS,default='trend'); parser.add_argument('--at')
    parser.add_argument('--nav-usd',type=float); parser.add_argument('--fx-capital-usd',type=float)
    args=parser.parse_args()
    if args.suite: result=suite(args.suite)
    elif args.replay: result=replay(args.replay)
    else:
        if not args.output: parser.error('--output required')
        kind='backtest'
        if args.input: request=json.loads(args.input.read_text(encoding='utf-8'))
        else:
            if args.nav_usd is None or args.fx_capital_usd is None: parser.error('Explicit --nav-usd and --fx-capital-usd required (flat account proposal only)')
            saved=json.loads(args.capture.read_text(encoding='utf-8')); body=saved['payload']
            if digest(body)!=saved['checksum']: raise ValueError('Capture integrity failure')
            settings=json.loads(args.config.read_text(encoding='utf-8')); kind='proposal'
            request=dict(candles=body['candles'],rates=body['rates'],model=args.model,
                         time=args.at or datetime.now(timezone.utc),capacity=asdict(Capacity(args.nav_usd,args.fx_capital_usd)),
                         config=settings['features'],execution=settings['execution'],risk=settings['risk'],volatility=settings['volatility'])
        document=bundle(request,kind); args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('xb') as stream: stream.write(encoded(document))
        result=dict(status='saved',kind=kind,path=str(args.output))
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
