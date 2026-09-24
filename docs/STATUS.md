# Execution status â€” 2026-09-23

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
backdated before ingestion. No live trading, FX execution, learned regime, Black-Litterman or broker
integration has been started. Phase 3 status follows.


## Phase 3: locally PASSED (package 0.5.0)

Independent next-open event engine and vectorized screening with costs,
contributions, safe return/carry, monthly/emergency decisions, stops/TP/time
exits, gap handling and reproducible reporting. 147 tests pass (28 new), with
45 synthetic simulations and 45 exact replays. Installed source equality,
pip check and a saved phase-1 replay pass. Remote CI not run.

See PHASE3_ACCEPTANCE.md and BACKTESTING.md for the precise daily execution
conventions and limits. This completes the phase-3 engineering gate, not an
investment-performance gate. Current data vintages remain unsuitable for
retroactive point-in-time claims. Next phase: Black-Litterman equity baseline.
