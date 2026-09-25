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


## Execution record — 2026-09-24, phase 4

Phase 4, package 0.6.0: locally PASSED. 184 tests (37 new), the published
Idzorek numeric example within rounding, 12 covariance/view comparisons and
3 monthly ledger cases, all 15 replayed exactly. Constraints and post-cost
CPPI/TIPP budget checks pass. Evidence: docs/PHASE4_ACCEPTANCE.md and
reports/phase4-validation.json. Model and execution choices are explicitly
identified in docs/BLACK_LITTERMAN.md. Phase 5 status is recorded in the newer checkpoint below.


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


## Execution record — 2026-09-24, phase 6

Phase 6, package 0.8.0: locally PASSED under docs/FX_BASELINE.md.
242 tests (31 new), three chronological holdouts, 15 cases and exact replays,
with cost sensitivity, causal timestamp/proposal replay and signed accounting.
Free Yahoo capture validated on 1,044 real candles. FRED live requests failed;
missing rates produce NO_TRADE, while normalization/rule tests use explicit
synthetic vintages. No real historical performance claim. Evidence:
docs/PHASE6_ACCEPTANCE.md and reports/phase6-validation.json.
Phase 7 has not started; research plans remain non-executable pending its
volatility/stop/sizing implementation. Brokerage remains behind later gates.


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
pass. See [phase-8 acceptance](docs/PHASE8_ACCEPTANCE.md) and
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
See [acceptance](docs/PHASE9_ACCEPTANCE.md) and reports/phase9-validation.json.
Earlier phase-9-not-started checkpoints are historical. Phase 10 not started.
No broker execution, new dependency, commit or push. FRED repair preserved.
