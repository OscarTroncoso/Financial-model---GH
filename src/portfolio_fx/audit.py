"""Canonical checksums and source identities for saved FX experiments."""
import hashlib
import json
from pathlib import Path
import portfolio_data


def encoded(value) -> bytes:
    return json.dumps(value,sort_keys=True,indent=2,allow_nan=False,default=lambda v:v.isoformat()).encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def source_hash() -> str:
    roots=(Path(__file__).parent,Path(portfolio_data.__file__).parent)
    return digest({root.name+'/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                   for root in roots for p in sorted(root.glob('*.py'))})
