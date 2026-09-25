"""Generate auditable research views, or run/replay chronological validation."""
import argparse
import json
from pathlib import Path
from .core import encoded
from .workflow import bundle,replay
from .report import acceptance_suite


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--input',type=Path); mode.add_argument('--replay',type=Path); mode.add_argument('--suite',type=Path)
    parser.add_argument('--config',type=Path,default=Path('config/systematic_views.json'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.suite: result=acceptance_suite(args.suite)
    elif args.replay: result=replay(args.replay)
    else:
        if args.output is None: parser.error('--input requires --output')
        document=bundle(json.loads(args.input.read_text(encoding='utf-8')),json.loads(args.config.read_text(encoding='utf-8')))
        with args.output.open('xb') as stream: stream.write(encoded(document))
        result={'status':'saved','model_status':document['payload']['result']['model']['status'],'output':str(args.output)}
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
