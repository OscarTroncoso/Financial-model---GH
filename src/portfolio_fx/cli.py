"""FX research CLI: capture, as-of proposal, walk-forward suite and replay."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import json
from pathlib import Path
from .contracts import Candle,Rate,FXConfig
from .signals import signal,MODELS,replay_signal
from .audit import digest,encoded
from .report import bundle,replay,suite
from .providers import capture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--suite',type=Path); modes.add_argument('--replay',type=Path)
    modes.add_argument('--capture',type=Path); modes.add_argument('--input',type=Path)
    modes.add_argument('--signal-capture',type=Path)
    parser.add_argument('--output',type=Path); parser.add_argument('--days',type=int,default=30)
    parser.add_argument('--model',choices=MODELS,default='trend'); parser.add_argument('--at')
    parser.add_argument('--config',type=Path,default=Path('config/fx.json'))
    args=parser.parse_args()
    if args.suite: result=suite(args.suite)
    elif args.replay:
        saved=json.loads(args.replay.read_text(encoding='utf-8'))
        result=replay_signal(saved) if 'signal_id' in saved else replay(args.replay)
    elif args.capture: result=capture(args.capture,args.days)
    else:
        if not args.output: parser.error('--output required')
        if args.input: document=bundle(json.loads(args.input.read_text(encoding='utf-8')))
        else:
            saved=json.loads(args.signal_capture.read_text(encoding='utf-8')); body=saved['payload']
            if digest(body)!=saved['checksum']: raise ValueError('Capture checksum mismatch')
            settings=json.loads(args.config.read_text(encoding='utf-8'))
            document=signal(tuple(Candle(**r) for r in body['candles']),tuple(Rate(**r) for r in body['rates']),
                args.at or datetime.now(timezone.utc),args.model,FXConfig(**settings['model']))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('xb') as stream: stream.write(encoded(document))
        result={'status':'saved','path':str(args.output)}
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
