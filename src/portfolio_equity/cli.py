"""Compute an auditable equity target, run synthetic acceptance, or replay."""
import argparse
import json
from pathlib import Path
from .contracts import EquityConfig
from .report import acceptance_suite,bundle,encoded,replay


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--suite',type=Path,help='New directory for synthetic acceptance cases')
    mode.add_argument('--input',type=Path,help='Explicit point-in-time allocation request JSON')
    mode.add_argument('--replay',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--config',type=Path,default=Path('config/equity.json'))
    args=parser.parse_args()
    if args.replay:
        result=replay(args.replay)
    else:
        config=EquityConfig(**json.loads(args.config.read_text(encoding='utf-8')))
        if args.suite: result=acceptance_suite(args.suite,config)
        else:
            if args.output is None: parser.error('--input requires --output (new JSON file)')
            document=bundle(json.loads(args.input.read_text(encoding='utf-8')),config)
            with args.output.open('xb') as stream: stream.write(encoded(document))
            result={'status':'saved','output':str(args.output),'allocation_id':document['payload']['result']['allocation_id']}
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__': main()
