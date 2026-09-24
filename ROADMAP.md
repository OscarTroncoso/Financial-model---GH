# ROADMAP.md
# Build plan and acceptance gates

## Principle
Build the system from foundations upward. Do not start with complex ML or live broker execution.

---

## Phase 0 â€” Repository and specification lock

### Deliverables
- `AGENTS.md`
- `PROJECT_SPEC.md`
- `ROADMAP.md`
- `README.md`
- configuration schema
- initial package structure
- CI test job

### Acceptance criteria
- repository installs in a clean environment,
- tests can run with one command,
- no secrets committed,
- project parameters have a documented config home,
- scope/terminology consistent with `PROJECT_SPEC.md`.

---

## Phase 1 â€” Portfolio Insurance Laboratory

### Goal
Create a self-contained research lab for CPPI family strategies before integrating equities or FX.

### Implement
- contribution-aware portfolio accounting,
- safe-asset return series,
- classical CPPI,
- HWM tracking,
- TIPP floor,
- drawdown floor,
- dynamic volatility multiplier,
- adaptive multiplier hooks,
- EPPI challenger interface,
- monthly ordinary rebalance,
- daily monitoring,
- emergency de-risking interface,
- insurance metrics,
- event/audit records.

### Mandatory benchmarks
- static allocation reference,
- classical CPPI,
- TIPP,
- volatility-adaptive CPPI,
- adaptive CPPI,
- EPPI.

### Tests
Hand-calculated tests for:
- floor,
- HWM,
- cushion,
- multiplier clipping,
- contributions,
- safe return,
- zero cushion,
- breach scenario,
- monthly rebalance logic,
- emergency action logic.

### Acceptance gate
Do not progress until:
- formulas match hand calculations,
- no look-ahead in risk estimates,
- contributions/rebalances are reproducible,
- stress cases run,
- comparison report is generated.

---

## Phase 2 â€” Data Foundation

### Implement
- raw/clean/feature storage conventions,
- timestamp/time-zone normalization,
- point-in-time availability fields,
- Parquet + DuckDB,
- data validators,
- metadata/versioning.

### Acceptance gate
- same input snapshot produces same features,
- stale/future data is detected,
- no future release time can enter a historical prediction row.

---

## Phase 3 â€” Backtesting Core

### Implement
- vectorized research runner,
- event-driven portfolio engine,
- costs,
- spread/slippage,
- cash/safe return,
- contribution events,
- rebalance events,
- gaps,
- stop/TP/time-stop abstractions,
- reporting.

### Acceptance gate
- deterministic test scenarios reconcile by hand,
- costs materially affect results where expected,
- monthly + emergency events work correctly.

---

## Phase 4 â€” Black-Litterman Equity Baseline

### Implement
- equity universe interface,
- market/equilibrium weights,
- covariance estimators,
- equilibrium returns,
- absolute/relative views,
- confidence/Omega,
- posterior,
- constrained optimizer,
- rebalance bands.

### Acceptance gate
- reproduce known toy BL example,
- posterior reacts correctly to view/confidence changes,
- target weights obey constraints,
- transaction-aware monthly rebalance works.

---

## Phase 5 â€” Equity Systematic Views

### Implement
- factor pipeline,
- normalized scores,
- mapping scores -> BL views,
- confidence model,
- view audit.

### Later
LLM-derived structured equity features.

### Acceptance gate
- every view can be traced to its input features and timestamp,
- no view uses unavailable future information.

---

## Phase 6 â€” EUR/USD Baseline

### Implement
- market-data pipeline,
- 30m/1H/4H/D feature alignment,
- simple momentum/trend baseline,
- simple mean-reversion baseline,
- simple macro/yield-spread baseline,
- `NO_TRADE` state,
- initial trade-plan object.

### Acceptance gate
- trades have reproducible signal timestamps,
- transaction costs included,
- baseline results reported walk-forward.

---

## Phase 7 â€” FX Volatility and Risk Engine

### Implement
- realized vol,
- EWMA,
- GARCH(1,1),
- stop interface,
- position sizing,
- risk limits,
- take-profit baseline,
- time stop.

### Acceptance gate
- stop -> position size relationship is correct by hand,
- loss at stop respects configured risk within execution assumptions,
- no fixed 5%-price stop is hard-coded.

---

## Phase 8 â€” FX Regime Engine

### Implement
- transparent rule-based regime,
- HMM challenger,
- optional clustering research.

### Acceptance gate
- regimes are inferred point-in-time,
- state probabilities stored,
- regime-dependent model performance can be measured.

---

## Phase 9 â€” Econometric Model Zoo

### Implement progressively
- AR/ARIMAX,
- VAR,
- Kalman/time-varying model,
- Markov switching,
- VECM only if cointegration tests + economic rationale pass.

### Acceptance gate
- all models evaluated through identical walk-forward interface,
- baselines retained,
- unstable models can be rejected automatically by predefined research rules.

---

## Phase 10 â€” ML Model Zoo

### Implement
- logistic/linear/Elastic Net,
- Random Forest,
- XGBoost/LightGBM,
- calibrated probability outputs where relevant,
- quantile/return targets where useful.

### Acceptance gate
- no random holdout used as primary evidence,
- hyperparameter selection is nested or appropriately time-aware,
- metrics reported by regime and net of costs.

---

## Phase 11 â€” Ensemble and Champion/Challenger

### Implement
- dynamic model weights,
- regime-conditioned performance,
- rolling OOS score,
- diversification/correlation penalty,
- weight caps,
- champion/challenger registry,
- promotion rules.

### Acceptance gate
- a short performance burst cannot cause uncontrolled model takeover,
- historical ensemble weights are reconstructible.

---

## Phase 12 â€” Meta-labeling and Advanced Trade Plan

### Implement
- triple-barrier research,
- meta-label model,
- probability/EV trade filter,
- advanced stop candidates,
- advanced TP candidates.

### Acceptance gate
- labeling leakage tests pass,
- meta-labeling adds robust OOS value or is rejected.

---

## Phase 13 â€” Fundamental / AI Feature Engine

### Implement
- structured schema,
- Fed/ECB text extraction,
- macro news extraction,
- relative policy score,
- equity news/earnings structured features,
- source/model/prompt version metadata.

### Acceptance gate
- AI output is structured and auditable,
- AI cannot bypass risk constraints,
- ablation test measures whether AI features add net OOS value.

---

## Phase 14 â€” Full Portfolio Integration

### Flow
Contribution
-> insurance engine
-> risky budget
-> equity / FX capacity
-> BL target
-> FX trade/no-trade
-> unused FX capital back to safe
-> risk validation
-> proposed orders
-> audit event.

### Acceptance gate
- full portfolio accounting reconciles,
- no sleeve can exceed portfolio-level hard limits,
- monthly rebalance + emergency protection coexist correctly.

---

## Phase 15 â€” Dashboard

### Implement
Mobile-friendly Streamlit MVP:
- overview,
- insurance,
- equities/BL,
- EUR/USD,
- models,
- risk,
- backtests,
- trades,
- audit.

### Acceptance gate
- dashboard is read-only initially,
- displayed state reconciles with engine state,
- works acceptably on mobile viewport.

---

## Phase 16 â€” Scheduled Automation

### Implement
- scheduled data refresh,
- scheduled signal checks,
- model retraining jobs,
- reports,
- failure notifications,
- GitHub Actions where appropriate.

### Acceptance gate
- jobs are idempotent,
- failed/stale input creates no trade,
- execution logs retained.

---

## Phase 17 â€” Shadow Mode

### Implement
Generate live recommendations without orders.

Store:
- signal,
- theoretical fill assumptions,
- realized subsequent path,
- model version,
- decision explanation.

### Acceptance gate
Run for a meaningful sample before paper automation.

---

## Phase 18 â€” IBKR Paper Trading

### Implement
- connectivity,
- order state machine,
- reconciliation,
- retries/idempotency,
- fill/slippage logging,
- kill switch.

### Acceptance gate
- paper fills reconcile with internal state,
- connection failures cannot duplicate orders,
- modeled vs realized costs are monitored.

---

## Phase 19 â€” Controlled Live Pilot

### Initial mode
Model recommends -> human confirms.

Only later consider:
Model creates order -> human approves.

Full automation is a separate approval decision.

### Acceptance gate
Explicitly defined before live capital is enabled.

---

## Phase 20 â€” Continuous Research

Ongoing:
- drift monitoring,
- challengers,
- new data/features,
- model retirement,
- risk review,
- cost review,
- parameter review.

No automatic self-deployment without governance.


## Execution record â€” 2026-09-23

- Phase 0: locally passed; remote CI has not been run.
- Phase 1, versions 0.1/0.2: core and conditional challenger completed while
  remaining model definitions were being verified.
- Phase 1, version 0.3.0: all required benchmark families implemented with exact
  variant identities in docs/DYNAMIC_MODELS.md. Local acceptance PASSED (88 tests, 720 replayed simulations). Evidence is in
  docs/PHASE1_ACCEPTANCE.md; execution status is in docs/STATUS.md.

The adaptive benchmark implements V4 with a neutral regime hook, following the
research ladder. EPPI selects the discrete 2023 publication's multiplier and
corrects the earlier unsupported exponential-cushion description. This does not
claim a canonical adaptive model or reproduction of inaccessible 2008 equations.
Neither empirical research questions nor later roadmap gates are waived.
At the 2026-09-23 checkpoint, phase 2 had passed and phase 3 had not started.

Phase 2, package 0.4.0: locally PASSED. 119 tests, 177 real observations from
free Yahoo/ECB sources, 174 reproducible feature rows. Temporal availability,
stale/future rejection, versioned Parquet and DuckDB are verified. Exact scope
and limitations: docs/PHASE2_ACCEPTANCE.md. See the newer checkpoint below.


## Execution record — 2026-09-24

Phase 3, package 0.5.0: locally PASSED under the explicit daily long-only
execution contract in docs/BACKTESTING.md. 147 tests (28 new), 45 synthetic cases
and 45 exact replays. Hand accounting, cost effects and monthly/emergency gates
pass. Evidence: docs/PHASE3_ACCEPTANCE.md and reports/phase3-validation.json.
No historical profitability claim or phase-4 implementation is implied.
