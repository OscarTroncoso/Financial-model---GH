# Session handoff — 2026-09-25, phase 9 complete for activated models

Installed distribution **0.11.0**; phases 0–9 locally accepted for implemented
models. VECM is disabled and its conditional research gate remains open.
Phase 10 not started. Read AGENTS.md, PROJECT_SPEC.md §20, ROADMAP.md,
ECONOMETRICS.md and PHASE9_ACCEPTANCE.md before extending the project.

New package: src/portfolio_econometrics/ (13 modules), tests/test_econometrics.py,
config/econometrics.json, config/examples/econometric_request.py.
Models: no-change, momentum, AR(1), ARX/restricted ARIMAX(1,0,0), VAR(1),
Kalman random-walk intercept/AR coefficient, switching Gaussian mean/variance.
All refit a known rolling window and forecast the next observed 4H log return.
Macro features are changes in historically available policy-rate differentials.
Rank/root/covariance/convergence/occupancy/magnitude failures abstain. VECM has
no enabling flag: economic rationale and cointegration work are still needed.

Phase-9 ledger snapshots phase 7 with ONLY proposal dispatch adapted, importing
its sizing and volatility functions. A source-body parity test prevents silent
execution/accounting divergence. Prior packages and replays remain untouched.
Phase-8 transparent rules annotate predictions/trades; no regime trade routing.

Verified: 318 tests (26 new), 24 chronological cases and 24 exact replays;
six additional rejection/disabled cases and replays. 85 installed source files
match, pip check passes, installed Markov evaluation and phase-8 inference replay
pass. Ordinary synthetic cases have zero actual risk-budget breaches.
Reports: reports/phase9-validation.json, phase9-comparison.md, phase9-metrics.json,
phase9-rejection-validation.json. Full bundles/source archive:
reports/runs/phase9-accepted-20260925/. Test log: reports/runs/phase9-tests-20260925.log.
Source identity: 13b7ab6a98fa8fa6bcb9647c4317db7f638f2f1ce0ebff5940e7644b05a6bc9f.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\portfolio-econometrics.exe --suite reports/runs/new-econometric-suite
.\.venv\Scripts\portfolio-econometrics.exe --replay reports/runs/phase9-accepted-20260925/fold-1--markov_switching--base.json
```

These are restricted research models and synthetic engineering evidence, not
profitable market validation. ARX/VAR first-equation predictions may coincide.
No holdout tuning, automatic promotion, phase-10 ML or live broker routing.
FRED remains repaired; current downloads cannot be backdated. No new dependency
or commit/push; preserve pre-existing uncommitted phase-4–8 work. Remote CI not run.
Next, only when requested: phase 10 ML challengers subject to its acceptance gates.

## Retained phase-8 and earlier context (historical)

# Session handoff — 2026-09-25, phase 8 complete

Phases 0–8 locally complete; installed package **0.10.0**. Phase 9 not started.
Read AGENTS.md, PROJECT_SPEC.md §19/§20, ROADMAP.md, FX_REGIMES.md and
PHASE8_ACCEPTANCE.md. Continue phase 9 only when the user requests it.

New code: src/portfolio_regimes/ (nine modules), tests/test_regimes.py,
config/fx_regimes.json and config/examples/fx_regime_request.py.
Gaussian HMM uses training-only Baum-Welch and forward holdout filtering,
with an independent transparent direction/volatility baseline. Inputs,
probabilities and fits are saved; net trade performance is attributed by the
actual entry decision. Financial/risk logic in prior packages was not modified.

Verified: 292 tests (23 new), 15 cases and 15 exact replays across three
chronological synthetic folds. All 72 installed Python sources match; pip check,
installed inference CLI replay, three-state smoke and an existing phase-7 GARCH
replay pass. Bundles/source archive: reports/runs/phase8-accepted-20260925/.
Tracked summaries: reports/phase8-validation.json, phase8-comparison.md,
phase8-metrics.json. Final test log: reports/runs/phase8-tests-final-20260925.log.
Source identity: fdb582c22a5d82bab139a8db5023ecb472cbcad194d53e057a307f5dc346e139.

Monday holdouts must train at the preceding completed pre-weekend close.
The initial review that incorrectly chose Monday midnight is kept in
reports/runs/phase8-review-weekend-cutoff-20260925/ and is NOT accepted evidence.
Current downloads cannot be backdated for HMM training; use genuine availability.
UNKNOWN is an explicit abstention. State ranks are relative per fit; no event,
stress or proven mean-reversion label is inferred. No economic promotion.

Commands:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\portfolio-regimes.exe --suite reports/runs/new-regime-suite
.\.venv\Scripts\portfolio-regimes.exe --replay reports/runs/phase8-accepted-20260925/fold-1--trend--base.json
```

FRED transport remains repaired, with zero source errors in the existing real
capture data/raw/fx-fred-verified-20260924/normalized.json. See retained phase-7
context below. No dependencies added. No commit/push performed; preserve all
pre-existing uncommitted phase-4–7 work. Remote CI not run. No broker routing.

## Retained phase-7 context (historical)

# Session handoff — 2026-09-25, phase 7 complete

Phases 0–7 locally complete; installed package **0.9.0**. Phase 8 not started.
Read AGENTS.md, PROJECT_SPEC.md, ROADMAP.md, FX_RISK.md and
PHASE7_ACCEPTANCE.md before extending the project.

The FRED prerequisite is resolved: standard Python HTTPS without an explicit
Accept: text/csv header captured 44 DFEDTARU + 44 ECBDFR observations, no errors.
Correction 0.8.1: 244 tests, 15 exact phase-6 replays. Current real capture:
data/raw/fx-fred-verified-20260924/normalized.json (Yahoo 1,044 candles, rates 88).
Raw normalization and macro proposal were replayed. Earlier failed captures
and older phase-6 status paragraphs are historical, not current blockers.
Public CSV needs no API key; the separate official API does require one.

Phase-7 code: src/portfolio_fx_risk/, tests/test_fx_risk.py, config/fx_risk.json.
Historical sample/EWMA/GARCH variance feeds a volatility stop and constrained
risk quantity. GARCH is variance-targeted finite-grid QML, not full MLE.
TP/time exits and adverse-gap accounting are explicit. The phase-6 fixed-size
engine remains separate and unchanged as a benchmark. No dependencies added.

Verified: 269 tests (25 new), 22 chronological/stress cases and exact replays,
63 installed Python source matches, pip check, installed GARCH replay and prior
phase-6 replay. Real-capture risk proposal saves/replays READY for an illustrative
flat USD 10,000 NAV / 1,000 FX capacity account; executable remains false.
Reports: reports/phase7-validation.json, phase7-comparison.md, phase7-metrics.json.
Full bundles/source snapshot: reports/runs/phase7-accepted-20260925/.
Normal holdouts: zero risk-budget breaches. Intentional 3% adverse gap: one.
Source changes require fresh bundles; do not alter saved historical evidence.

Commands from repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --suite reports/runs/new-risk-suite
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --replay reports/runs/phase7-accepted-20260925/fold-1--trend--garch--base.json
```

Reinstall after source edits before testing without PYTHONPATH. Remote CI not
run. Prior phase-4/5/6 and new phase-7 changes remain uncommitted; no commit/push
was performed. Existing .git state and user changes were preserved.

Next roadmap task, when requested: phase 8 regime engine. No later-phase model
or broker work was started. Risk-sized plans are research only; shadow/paper
acceptance remains required. USD linear FX collateral accounting is not EUR
portfolio integration or broker-specific settlement. No stop guarantees against
gaps, delayed exits or underestimated costs. Performance tests remain synthetic;
current Yahoo/FRED capture does not create historical release vintages.
