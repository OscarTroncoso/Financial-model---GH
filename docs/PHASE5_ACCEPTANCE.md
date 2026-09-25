# Phase 5 acceptance — 2026-09-24

**Locally PASSED, package 0.7.0.** Scope: reproducible price-factor baseline
for systematic Black-Litterman views. Phase 6 has not started.

| Requirement | Implementation and evidence |
|---|---|
| Factor pipeline | Adjusted-price momentum and sample volatility; explicit vintages, units, currency and freshness checks |
| Normalized scores | Directed cross-sectional population z-scores, configured clipping and weighted composite; hand examples |
| Scores to BL views | Fixed-pair OLS trained on completed, non-overlapping labels; annual relative mean passed to phase 4 |
| Confidence | Documented conditional-mean uncertainty proxy, SE floor and confidence cap; preserves effective Omega |
| Complete view audit | Raw price paths, feature vintages, configuration, coefficients, sample IDs, source hash and runtime saved |
| No future information | As-of filtering before vintage selection; historical predictors and known-label embargo; future-suffix invariance tests |
| Reproducibility | Six chronological fold bundles, six exact replays, descriptor CLI save/replay; 43 installed source files match workspace |

Validation: **211 tests pass, including 27 new phase-5 tests**. Dependency
check passes. Saved phase-3 and phase-4 runs still replay exactly. Remote CI
has not been run. See ../reports/phase5-validation.json and
../reports/phase5-comparison.md. Full bundles and the source snapshot are local
under reports/runs/phase5-accepted-20260924/ (ignored by Git; regenerate with
the suite command in SYSTEMATIC_VIEWS.md).

The six synthetic chronological folds compare forecast MSE against zero and
historical-mean baselines. Separate flat-mark ledger examples compare no-view,
systematic-view and higher-cost execution. They do not estimate market trading
profits. Low fitted confidence remains low when passed to Black-Litterman.

The price descriptors, linear mapping, annual scaling and uncertainty proxy are
explicit baseline conventions, not a claim that a published investment model
has been replicated. Exact equations, units, hand examples and primary-source
identities are in MODELS.md, SYSTEMATIC_VIEWS.md and references.json.

NO_VIEW falls back to the existing no-view prior for insufficient, stale,
constant or extrapolated training information or forecasts outside configured
bounds. Invalid input fails closed. Portfolio caps and post-cost CPPI/TIPP
checks remain enforced by phase 4.

## Remaining research boundaries

Real-market predictive performance and confidence calibration are unestablished.
No real equity universe was selected. Current vendor downloads do not certify
past availability; historical vintages must not be invented. Fundamental and
LLM features, multiple correlated views and execution against a broker are not
part of this price-only baseline. These limits do not waive subsequent roadmap
acceptance gates or authorize live capital deployment.
