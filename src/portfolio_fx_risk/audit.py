"""Hash the risk package and its financial/data dependencies."""
from pathlib import Path
import hashlib
import portfolio_fx,portfolio_data
from portfolio_fx.audit import encoded,digest


def source_hash() -> str:
    roots=(Path(__file__).parent,Path(portfolio_fx.__file__).parent,Path(portfolio_data.__file__).parent)
    return digest({r.name+'/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for r in roots for p in sorted(r.glob('*.py'))})
