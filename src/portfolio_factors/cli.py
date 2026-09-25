"""Save/replay factor score snapshots. This command cannot generate BL views."""
import argparse
import json
from pathlib import Path
import platform
import numpy as np
from portfolio_equity.contracts import Universe
from .core import Feature,config_from_dict,digest,encoded,snapshot


def build(request: dict,config: dict) -> dict:
    if set(request)!={'universe','features','decision_time'}:
        raise ValueError('Unknown or missing snapshot request fields')
    result=snapshot(Universe(**request['universe']),tuple(Feature(**f) for f in request['features']),
                    request['decision_time'],config_from_dict(config))
    payload={'request':request,'config':config,'snapshot':result,
             'runtime':{'python':platform.python_version(),'numpy':np.__version__}}
    payload=json.loads(encoded(payload))
    return {'checksum':digest(payload),'payload':payload}


def replay(path: Path) -> dict:
    document=json.loads(path.read_text(encoding='utf-8')); payload=document['payload']
    if digest(payload)!=document['checksum']: raise ValueError('Bundle checksum mismatch')
    if build(payload['request'],payload['config'])!=document: raise ValueError('Source, runtime or result mismatch')
    return {'status':'verified','snapshot_id':payload['snapshot']['snapshot_id']}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--input',type=Path); mode.add_argument('--replay',type=Path)
    parser.add_argument('--config',type=Path,default=Path('config/factors.json'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.replay: result=replay(args.replay)
    else:
        if args.output is None: parser.error('--output is required with --input')
        result=build(json.loads(args.input.read_text(encoding='utf-8')),json.loads(args.config.read_text(encoding='utf-8')))
        with args.output.open('xb') as stream: stream.write(encoded(result))
        result={'status':'saved','snapshot_id':result['payload']['snapshot']['snapshot_id'],'contains_bl_views':False}
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
