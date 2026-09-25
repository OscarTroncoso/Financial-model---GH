# Execution status — 2026-09-25

## Phase 0: locally passed

Typed standard-library Python package, strict config, isolated Python 3.12
installation, offline wheel installation and CI test definition are present.
Remote GitHub Actions execution is not claimed.

## Phase 1: locally PASSED (0.3.0)

Version 0.3.0: 88 unit/integration tests passed. All eight model IDs execute:
static, cppi, tipp, drawdown, conditional_cppi, volatility_adaptive, adaptive,
eppi. Exact identities and explicit project choices: DYNAMIC_MODELS.md.

The mandatory adaptive benchmark is V4 (volatility plus drawdown); regime is a
neutral hook, not a learned predictor. EPPI is the selected discrete 2023 rule;
the unavailable 2008 original is not claimed as verified. Sources, derivations,
units, edge cases and hand examples are documented. 22 bibliography records.

The full sensitivity suite contains nine configurations x ten synthetic paths
x eight models. All 720 runs were saved and replayed successfully. The verified completion
artifact is reports/phase1-validation.json; full bundles reside under
reports/runs/phase1-accepted-20260923/. See PHASE1_ACCEPTANCE.md for the gate
matrix, model decisions, findings and limits. No phase-1 implementation remains
open under those explicitly documented variant choices.

The 50 saved version-0.2.0 runs retain exactly the same financial events and
existing metrics after projecting out newly added audit/metric fields.
Installed Python sources match workspace sources byte for byte.

## Phase 2: locally PASSED (package 0.4.0)

Free daily sources yfinance and ECB verified with real downloads. Immutable
bronze payloads, typed silver/gold Parquet, DuckDB catalog/as-of queries, UTC
availability contracts, revision selection, freshness/quality validators,
checksums and feature replay are implemented in portfolio_data.

119 tests pass (88 existing + 31 data). Three real series, 177 observations,
174 feature rows and exact replay. Details: PHASE2_ACCEPTANCE.md,
DATA_FOUNDATION.md and DATA_SOURCES.md. Versioned dependencies are recorded in
requirements-data.lock; pip check passes. Remote CI not claimed.

## Limits and next boundary

Phase-1 performance evidence remains synthetic. Phase 2 adds real data plumbing,
not a historical strategy evaluation or an investment edge. Current vendor
histories do not supply certified historical vintages; availability is never
backdated before ingestion. At the phase-2 checkpoint, later strategy and broker modules had not started.
Newer phase-3 and phase-4 status follows.


## Phase 3: locally PASSED (package 0.5.0)

Independent next-open event engine and vectorized screening with costs,
contributions, safe return/carry, monthly/emergency decisions, stops/TP/time
exits, gap handling and reproducible reporting. 147 tests pass (28 new), with
45 synthetic simulations and 45 exact replays. Installed source equality,
pip check and a saved phase-1 replay pass. Remote CI not run.

See PHASE3_ACCEPTANCE.md and BACKTESTING.md for the precise daily execution
conventions and limits. This completes the phase-3 engineering gate, not an
investment-performance gate. Current data vintages remain unsuitable for
retroactive point-in-time claims. The next checkpoint below records the Black-Litterman equity baseline.


## Phase 4: locally PASSED (package 0.6.0)

Black-Litterman prior/posterior, absolute/relative views, explicit confidence
mapping, sample/EWMA/spherical Ledoit-Wolf covariance, causal universe/data
contracts, capped long-only optimizer and contribution-aware delayed rebalance
ledger are implemented. 184 tests pass (37 new), with 12 comparison cases,
3 monthly cases and 15 exact replays. Published Idzorek example matches within
source rounding. Package/source equality and dependency checks pass; earlier
phase-1/phase-3 saved replays still verify. Remote CI not run.

See PHASE4_ACCEPTANCE.md and BLACK_LITTERMAN.md for identities and limits.
This is numerical and synthetic engineering evidence, not historical investment
performance. No real equity universe has been chosen for the user. The newer phase-5 checkpoint follows; FX strategies and brokerage remain later.


## Phase 5 checkpoint — 2026-09-24, package 0.7.0

Locally PASSED: price-factor pipeline, normalized scores, chronological OLS
relative view, uncertainty/confidence mapping and complete input/model audit.
211 tests pass (27 new); six synthetic walk-forward folds and six exact replays.
Descriptor CLI replay, installed source equality (43 files), dependency check
and saved phase-3/phase-4 replays pass. Remote CI not run.
Evidence: docs/PHASE5_ACCEPTANCE.md (PHASE5_ACCEPTANCE.md from docs/),
reports/phase5-validation.json and reports/phase5-comparison.md.
This closes the engineering phase, not market profitability or confidence
calibration. At that checkpoint phase 6 had not started. Resume context: docs/SESSION_HANDOFF.md.

## Phase 6: locally PASSED (package 0.8.0)

EUR/USD free intraday capture, complete causal 30m/1H/4H/D alignment, trend,
mean-reversion and policy-rate-proxy baselines, NO_TRADE, audited research
proposals and a delayed signed USD-collateral ledger are implemented.
242 tests pass (31 new), three chronological folds yield 15 saved cases and
15 exact replays. Dependency/source checks (53 Python files), ready/NO_TRADE
proposal replays and an earlier phase-5 replay pass. Remote CI not run.

Yahoo capture: 1,044 real candles, normalization replay verified. FRED endpoints
failed, so real rates remain absent and the macro proposal remains NO_TRADE.
Live FRED capture is not claimed as verified. Synthetic financial evaluation
does not establish market profitability. Contract: FX_BASELINE.md; gate report:
PHASE6_ACCEPTANCE.md. Phase 7 risk sizing/stops has not started. Plans remain
non-executable and no brokerage integration has been enabled.


## FRED correction verified — package 0.8.1

Supersedes earlier statements that live FRED acquisition was unverified.
The standard Python HTTPS client without an explicit Accept: text/csv header
successfully captured both series: 44 DFEDTARU and 44 ECBDFR observations,
with no source errors. Original HTTP/2 failures and the Accept-header timeout
were transport issues, not missing subscriptions. Normalization and the real
macro proposal replay passed; ingestion timestamps remain actual capture times.
244 tests and 15 regenerated phase-6 exact replays passed. Evidence:
reports/fred-fix-validation.json; current bundles:
reports/runs/phase6-fred-verified-20260924/. No API key was needed for public CSV.
This verifies present acquisition, not historical release vintages or uptime.
The phase-7 completion checkpoint follows.


## Phase 7 checkpoint — 2026-09-25, package 0.9.0

Locally PASSED under docs/FX_RISK.md (FX_RISK.md from docs/). Historical/EWMA/
restricted GARCH variance, volatility stop, constrained cost/carry-aware sizing,
TP/time exit and gap-aware signed ledger implemented. 269 tests (25 new), three
chronological holdouts plus adverse gap stress: 22 cases and 22 exact replays.
All normal holdouts have zero actual budget breaches; the gap stress has one,
explicitly demonstrating the limits of stop protection. 63 installed source
files match; pip check, prior corrected phase-6 replay and real-data proposal
replay pass. FRED acquisition is repaired: 88 real observations, no errors.
Evidence: docs/PHASE7_ACCEPTANCE.md and reports/phase7-validation.json.
No market profitability or brokerage readiness claimed. Phase 8 not started.


## Phase 8 checkpoint — 2026-09-25

Locally PASSED, package 0.10.0. Transparent FX regime rules and a Gaussian HMM
challenger infer as-of states and save their probabilities, fitted parameters,
source identity and input lineage. Entry-decision attribution measures unchanged
phase-7 strategies after costs/carry, with safe income separately reconciled.
292 tests pass (23 phase-8), 15 cases / 15 exact replays across three chronological
synthetic holdouts. The pre-weekend training-cutoff regression is covered.
72 installed source files match; dependencies and an existing phase-7 replay
pass. See [phase-8 acceptance](PHASE8_ACCEPTANCE.md) and
reports/phase8-validation.json. Earlier phase-8-not-started entries are historical.
No profitability claim, risk override or broker routing. Optional clustering is
deferred. Phase 9 has not started. FRED remains repaired as recorded in phase 7.


## Phase 9 checkpoint — 2026-09-25

Locally PASSED for activated models, package 0.11.0: AR(1), restricted
ARIMAX(1,0,0)/ARX, VAR(1), Kalman time-varying AR and Gaussian Markov-switching
mean/variance. Identical rolling walk-forward interface, retained no-change and
momentum baselines, cost-inclusive risk ledger and predefined rejection rules.
VECM remains disabled with its economic/cointegration research gate open.
318 tests (26 new), 24 chronological cases / exact replays, six additional saved
rejection/disabled cases / replays. 85 installed source files match; pip check,
installed Markov evaluation and prior phase-8 replay pass. No economic promotion.
See [acceptance](PHASE9_ACCEPTANCE.md) and reports/phase9-validation.json.
Earlier phase-9-not-started checkpoints are historical. Phase 10 not started.
No broker execution, new dependency, commit or push. FRED repair preserved.
