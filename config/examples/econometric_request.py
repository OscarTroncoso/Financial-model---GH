"""Create a synthetic AR forecast request from the repository root."""
from dataclasses import asdict
from pathlib import Path
import json
from portfolio_fx.report import fixture
from portfolio_fx.audit import encoded

rows,rates=fixture()
request=dict(candles=[asdict(r) for r in rows],rates=[asdict(r) for r in rates],
             model='ar',time=rows[13*48-1].end,
             econometrics=json.loads(Path('config/econometrics.json').read_text(encoding='utf-8')))
output=Path('reports/runs/econometric-request.json'); output.parent.mkdir(parents=True,exist_ok=True)
with output.open('xb') as stream: stream.write(encoded(request))
