# Phase 9 acceptance — 2026-09-25

**Locally PASSED for the activated models, package 0.11.0.** Contract and exact
scope: [ECONOMETRICS.md](ECONOMETRICS.md). VECM's conditional research gate
remains open and the model is disabled. Phase 10 has not started.

| Acceptance requirement | Implementation and verification |
|---|---|
| AR / ARIMAX | AR(1) and explicit ARX / ARIMAX(1,0,0) specialization; lagged known exogenous input; OLS hand cases |
| VAR | Bivariate VAR(1) in returns and rate-differential changes; matrix recursion and root checks |
| Kalman/time-varying | Random-walk intercept/AR coefficient filter; scalar/vector hand updates and covariance checks |
| Markov switching | Gaussian switching mean/variance, filtered endpoint propagated one step; total mixture variance verified |
| Conditional VECM | Disabled with an explicit reason; no false cointegration claim or enabling flag |
| Identical walk-forward interface | All active models use rolling as-of windows, common decisions/target/scoring and the same risk ledger |
| Baselines retained | No-change and momentum controls; previous phase-6/7 packages untouched |
| Automatic instability rejection | Rank, root, covariance, convergence, occupancy and magnitude gates; completed-holdout coverage/drawdown screening |
| Costs and risk | Existing stops, sizing, carry, safe income, spread/slippage/fees, limits and kill switch; ledger-body parity test |
| Reproducibility | Full raw requests, fitted inputs/parameters, configs, source/runtime identity and exact replay |

**318 tests pass, including 26 new phase-9 tests** (67.652 seconds).
**24 chronological cases and 24 exact replays** cover three holdouts, seven
active models and elevated costs for AR. Each holdout has two synthetic trading
days after training/warmup. There are 288 decision records and 264 scored
forecasts across cases; these include repeated timestamps across comparisons,
not that many independent market observations. Every active model produces
valid forecasts. Ordinary cases have zero actual risk-budget breaches.

Six additional saved cases replay exactly: explosive AR rejection, unavailable
macro history, constant macro feature rejection, nonconverged Markov rejection,
excessive forecast rejection and disabled VECM. Their purposes are distinct from
economic model promotion. See [rejection evidence](../reports/phase9-rejection-validation.json).

The installed package has 85 Python source files identical to the workspace.
Dependency check passes. A full installed Markov evaluation replay and a saved
phase-8 inference replay pass. No prior financial package was modified.
The phase-9 ledger only adapts proposal dispatch; tests enforce exact accounting
and barrier-body parity with phase 7. This snapshot must be kept synchronized
if execution semantics are deliberately changed in the future.

Evidence: [validation](../reports/phase9-validation.json),
[comparison](../reports/phase9-comparison.md), [metrics](../reports/phase9-metrics.json).
Full bundles/source archive: reports/runs/phase9-accepted-20260925/.
Tests: reports/runs/phase9-tests-20260925.log.
Source: `13b7ab6a98fa8fa6bcb9647c4317db7f638f2f1ce0ebff5940e7644b05a6bc9f`.
Remote CI not run. No new dependency, commit, push or broker routing.

## Material limits

Acceptance is synthetic engineering validation. Forecast skill, stationarity,
calibration and economic value on real point-in-time data remain unproven.
Orders are deliberately restricted, Q/R are configured assumptions, and
Markov training uses one deterministic initialization. ARIMAX and VAR can
produce the same first-equation forecast; this is not independent confirmation.

VECM requires a defensible relationship and cointegration evidence before any
implementation/activation. General ARIMA/MA order selection and switching AR(4)
are not claimed. Variance definitions and uncertainty omissions are explicit.
Data gaps, execution delay and configured maximum holding time mean a next-bar
forecast is not an exactly matching executed position horizon. Stop orders can
still lose beyond their modeled budget in a gap, as demonstrated in phase 7.
Completed-holdout research rejection does not retroactively alter trades and
is not the later champion/challenger promotion system.

All activated equations are verified against accessible primary implementation
sources and documented in MODELS.md. FRED's earlier repair remains intact;
current downloads still do not establish historical publication vintages.
