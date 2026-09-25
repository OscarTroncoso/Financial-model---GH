# Phase 6 acceptance — 2026-09-24

**Locally PASSED, package 0.8.1**, under the research contract in
[FX_BASELINE.md](FX_BASELINE.md). Phase 7 is recorded in PHASE7_ACCEPTANCE.md.

| Phase-6 requirement | Evidence |
|---|---|
| Market-data pipeline | Free Yahoo 30m EURUSD adapter, immutable raw/normalized capture; 1,044 real candles and exact normalization replay |
| 30m/1H/4H/D alignment | Complete UTC buckets, lineage, availability and freshness; partial/missing/future candles tested; real capture exercised all four frames |
| Momentum/trend baseline | Fixed 4H SMA-ratio rule with configurable windows/deadband |
| Mean-reversion baseline | Trailing population-price z-score with explicit contrarian convention |
| Macro/rate baseline | Known EUR-minus-USD policy proxy with fresh-vintage selection; hand test and chronological synthetic evaluation |
| NO_TRADE | Flat benchmark and fail-safe missing/stale information; actual missing-rate proposal saved and replayed |
| Initial trade plan | Timestamp, direction, reference entry, features, evidence, config/version and source hash; explicitly non-executable until phase-7 risk sizing |
| Reproducible signal timestamps | Prefix invariance, complete-input replay and both ready/NO_TRADE proposal replay |
| Transaction costs included | Both-side commission, spread/slippage, separate long/short carry, safe collateral return, later execution and account reconciliation |
| Walk-forward reporting | Three independent chronological holdouts, four fixed rules and three elevated-cost comparisons: 15 cases and 15 exact replays |

**242 tests pass, including 31 new FX tests.** Additional hand assertions for
Sharpe/Sortino/Calmar and win/loss ratio passed after the full suite. Installed
Python sources match all 53 workspace files. Dependency check and a saved
phase-5 replay pass. Remote CI has not been run.

Reports: [validation](../reports/phase6-validation.json),
[comparison](../reports/phase6-comparison.md), [all metrics](../reports/phase6-metrics.json).
Full raw-input experiment bundles and source snapshot reside locally in
reports/runs/phase6-accepted-20260924/ and are Git-ignored. The suite command
regenerates synthetic evidence. Every high-cost case incurred more costs and
lower net return than its corresponding base-cost case. This is accounting
sensitivity evidence, not a claim of trading advantage.

## Live data limitations retained

Yahoo provided 1,044 completed 30m candles. Another 396 all-missing quote rows
were preserved in the raw library-output snapshot and excluded without filling.
This validates data plumbing, not historical strategy returns. All downloaded
observations retain actual ingestion and fail historical close-vintage replay.

FRED transport is now verified: 44 DFEDTARU and 44 ECBDFR observations,
with zero source errors and exact normalization/macro-proposal replay. Standard
Python HTTPS requests without an explicit Accept: text/csv header succeeded;
prior curl transport and header-dependent timeout failures are retained as
diagnostics. No API key was needed for public CSV. Corrected evidence is in
reports/fred-fix-validation.json and reports/runs/phase6-fred-verified-20260924/.
The correction passes 244 tests and regenerates all 15 exact phase-6 replays.

## Financial and next-phase boundaries

All rule identities, equations and primary-source qualifications are documented
in MODELS.md and REFERENCES.md. Parameters/costs are illustrative assumptions.
The macro feature is an asymmetric policy-rate proxy, not matched bond yields,
UIP or a broker swap quote. Synthetic tests do not establish profitability.

The ledger uses USD collateral and signed EUR exposure; it does not integrate
with the user's EUR portfolio or provide physical spot settlement. Plans have
no stops, take-profit or risk-sized quantity yet and are marked non-executable.
Those fields depend on phase 7. No live brokerage orders or automation exist.


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
Phase 7 completion is recorded separately in PHASE7_ACCEPTANCE.md.
