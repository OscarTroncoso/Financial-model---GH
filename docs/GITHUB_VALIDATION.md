# GitHub research validation

Run **Research validation (phases 0-9)** from the Actions tab. Manual runs can
include or omit current Yahoo/FRED downloads. The initial review branch also
runs automatically when this workflow or its runner changes; there is no schedule.

Nine isolated jobs run the existing unit tests and phase-1/3/4/5/6/7/8/9
acceptance suites. Phase-2 data contracts are covered by unit tests and the live
provider diagnostic. The financial code and default parameters are unchanged.
Suite reports include their original exact replay checks. Each artifact contains
logs, reports, immutable experiment inputs, runtime metadata and source snapshots.
Artifacts expire after 30 days; download evidence you want to retain permanently.

The separate live job attempts a current public Yahoo/FRED capture without
credentials. If Yahoo prevents combined capture, it still probes both FRED
series independently. Missing/failed sources fail that job and remain visible;
no synthetic data replaces a failed download. Artifacts are uploaded even after
failure. Four phase-7 research proposals and eight econometric forecasts are
saved and replayed when a normalized capture is available. Account inputs are
explicitly illustrative: USD 10,000 NAV, USD 1,000 FX capacity, flat account.
No broker connection or order is created.

A successfully captured snapshot may still produce NO_TRADE, UNAVAILABLE,
REJECTED or DISABLED results. Current downloads cannot establish historical
macro availability. Such abstentions are reported honestly; provider success
is not proof of strategy readiness or profitability. Synthetic acceptance is
engineering evidence, not economic validation or whole-portfolio integration.

The local equivalent is:

```powershell
python scripts/validate_research.py --suite equity --output reports/runs/new-equity-check
python scripts/validate_research.py --suite live --output reports/runs/new-live-check
```

All output directories must be new. An optional `--existing-capture` can exercise
live-diagnostic processing offline and is explicitly labeled as replay of an old
snapshot, never a new download. No secrets or personal account settings are used.
