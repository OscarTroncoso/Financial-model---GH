"""Create a synthetic inference request; run from the repository root."""
from dataclasses import asdict
import json
from pathlib import Path
from portfolio_fx.report import fixture
from portfolio_fx.audit import encoded

rows,_=fixture()
request=dict(candles=[asdict(r) for r in rows],times=[rows[13*48-1].end],
             training_cutoff=rows[12*48].start,
             config=json.loads(Path('config/fx_regimes.json').read_text(encoding='utf-8')))
output=Path('reports/runs/regime-request.json')
output.parent.mkdir(parents=True,exist_ok=True)
with output.open('xb') as stream: stream.write(encoded(request))
