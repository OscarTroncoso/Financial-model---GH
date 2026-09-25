"""Source identity across econometric and existing financial dependencies."""
from pathlib import Path
import hashlib
import portfolio_fx,portfolio_fx_risk,portfolio_regimes,portfolio_data
from portfolio_fx.audit import encoded,digest


def source_hash() -> str:
    roots=[Path(__file__).parent]+[Path(m.__file__).parent for m in (portfolio_fx,portfolio_fx_risk,portfolio_regimes,portfolio_data)]
    return digest({r.name+'/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for r in roots for p in sorted(r.glob('*.py'))})
