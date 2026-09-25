"""Research FX regimes: transparent rules, HMM, attribution and exact replay."""
import argparse,json
from pathlib import Path
from .workflow import bundle,replay
from .audit import encoded


def main():
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--input',type=Path); modes.add_argument('--replay',type=Path); modes.add_argument('--suite',type=Path)
    parser.add_argument('--kind',choices=('inference','evaluation'),default='inference'); parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.replay: result=replay(args.replay)
    elif args.suite:
        from .report import suite
        result=suite(args.suite)
    else:
        if not args.output: parser.error('--output required')
        document=bundle(json.loads(args.input.read_text(encoding='utf-8')),args.kind)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('xb') as stream: stream.write(encoded(document))
        result=dict(status='saved',path=str(args.output),kind=args.kind)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
