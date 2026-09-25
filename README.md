# Quant Portfolio System â€” Codex Context Pack

Latest local checkpoint: **phases 0–9 complete for activated models, package 0.11.0**. See
[execution status](docs/STATUS.md) and [session handoff](docs/SESSION_HANDOFF.md).

This repository is intended to become an adaptive portfolio-management and EUR/USD swing-trading system.

Read in this order:
1. `AGENTS.md` â€” permanent repository engineering/research rules.
2. `PROJECT_SPEC.md` â€” full financial/product specification.
3. `ROADMAP.md` â€” phased implementation plan and acceptance gates.
4. `CODEX_BOOTSTRAP_PROMPT.md` â€” first task prompt for Codex.

## Important
Do not ask Codex to build the entire system at once. Start with Phase 0 and Phase 1, validate them, commit, then proceed phase by phase.

The first real research product is the Portfolio Insurance Laboratory:
CPPI vs TIPP vs dynamic/adaptive CPPI vs EPPI, with monthly contributions/rebalancing, daily risk monitoring, safe-asset yield, realistic accounting, stress tests and auditability.


## Phase 1 laboratory (0.3.0)

Phase 0 is locally verified. Phase 1 includes the static benchmark, CPPI,
TIPP/drawdown, conditional CPPI, normalized inverse-volatility CPPI, adaptive V4
and discrete EPPI. Monthly contributions, safe returns, trading costs, daily
monitoring, delayed execution, emergency exits and replayable audit are included.

See [acceptance evidence](docs/PHASE1_ACCEPTANCE.md),
[exact model identities and sources](docs/DYNAMIC_MODELS.md),
[financial conventions](docs/IMPLEMENTATION.md) and [status](docs/STATUS.md).
Adaptive is an explicitly identified project composition of sourced components;
EPPI reproduces the selected 2023 discrete multiplier, not the unavailable 2008
original. Phase 2 data infrastructure is now implemented; learned regimes and broker execution remain later phases.

## Install and test

Python 3.12+. The financial core uses the standard library. Data connectors and
DuckDB have pinned dependencies in requirements-data.lock and pyproject.toml.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-data.lock
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m portfolio_lab.cli --config config/lab.json --output reports/runs/my-first-run
```

On Linux/macOS use `.venv/bin/python`. A local `.venv` has already been prepared
in this workspace. The system Python alias is unavailable here; it was created
using the bundled Python 3.12 runtime. Network-restricted installation was tested
by building a wheel with the bundled setuptools 84.0.0, then installing that
wheel into this otherwise clean environment with `--no-index --find-links dist`.
GitHub Actions defines the regular online install/test workflow; it has not yet
been run remotely.

The output directory must be new. Each run saves `comparison.md`, `manifest.json`,
source snapshots and eighty JSON bundles (ten synthetic scenarios x eight models).
Each bundle contains configuration, observations, hashes, events and all metrics.
The synthetic figures test mechanics; they are not historical performance,
calibration evidence or evidence of an investment edge.

Configuration is in `config/lab.json`, validated by `LabConfig`. Defaults
(10,000 EUR initial capital, 100 EUR monthly, 3% net annual defensive return,
80% floor and multiplier 3) are illustrative, not personal recommendations.
Only verified elasticity 1 and a neutral regime hook are accepted. The risky
asset is an aggregate test proxy: the reference equity/FX capacities are not
actual FX positions, nor a full 60/30/10 integration.

Verify a saved run against the exact installed code and saved inputs:

```powershell
.\.venv\Scripts\python.exe -m portfolio_lab.cli --replay reports/runs/my-first-run/overnight_gap--cppi.json
```

Bibliografia: [fuentes y estado de acceso](docs/REFERENCES.md),
[catalogo estructurado](docs/references.json), [BibTeX](docs/references.bib).


## Conditional multiplier challenger (0.2.0)

The laboratory now also runs `conditional_cppi`: a published quantile bound
with a documented rolling Gaussian baseline. Its current defaults use a 1%
lower tail and a 21-observation horizon. These are research inputs, not a claim
of 99% protection. See [formula and tests](docs/CONDITIONAL_CPPI.md) and
[EPPI review](docs/EPPI_REVIEW.md). No later roadmap phase is started.

Version 0.1.0 bundles retain their original source snapshots. Replay deliberately
requires matching source/version; use a new output directory for version 0.3.0.


## Complete phase-1 validation

```powershell
.\.venv\Scripts\python.exe -m portfolio_lab.cli --config config/lab.json --suite reports/runs/my-validation
```

Runs nine predefined sensitivity profiles (720 simulations) and verifies every
saved run by replay. It writes validation.json only after successful completion.
See [comparison](reports/phase1-final-comparison.md),
[sensitivity](reports/phase1-final-sensitivity.md) and
[acceptance review](docs/PHASE1_ACCEPTANCE.md). Full local audit bundles are under
reports/runs/phase1-accepted-20260923/; this directory is ignored by Git and can be
regenerated with the command above. Tracked reports and validation summary remain
in reports/. Older experimental snapshots are retained separately.

Phase-1 acceptance covers synthetic mechanical correctness, not empirical
investment usefulness. Gaps after entry can breach the floor; warmup and buy
vetoes can also leave a strategy entirely safe. No champion is selected here.


## Phase 2: free real-data foundation (0.4.0)

Free daily yfinance and ECB connectors are working. Configuration:
[config/data.json](config/data.json). The example instruments are pipeline test
inputs, not portfolio recommendations. No subscription or API key is needed.

```powershell
.\.venv\Scripts\python.exe -m portfolio_data.cli download --start 2026-07-01 --end 2026-09-22
.\.venv\Scripts\python.exe -m portfolio_data.cli list
```

Dates are start-inclusive/end-exclusive. The first real sample has 177 clean
observations and 174 feature rows. Downloads, Parquet, catalog and provider cache
remain local under data/ and are excluded from Git. Input availability is based
on actual ingestion; a currently revised historical price is not falsely made
available to a historical decision.

See [phase-2 acceptance](docs/PHASE2_ACCEPTANCE.md),
[data contracts and replay commands](docs/DATA_FOUNDATION.md),
[free sources and TradingView assessment](docs/DATA_SOURCES.md), and
[validation record](reports/phase2-validation.json).
119 tests pass. The financial module remains version 0.3.0 unchanged inside the
0.4.0 distribution, preserving the phase-1 experiment source hashes.


## Phase 3 backtesting core (0.5.0)

The next-open event engine and vectorized research layer are locally accepted:
147 passing tests, 45 synthetic scenarios and 45 exact replays. Includes separate
trading costs, overnight safe income/carry, contributions, monthly/emergency
orders, gap-aware stops, take-profit and time exits. The phase-1 lab is unchanged.

```powershell
.\.venv\Scripts\python.exe -m portfolio_backtest.cli --output reports/runs/my-backtest-suite
.\.venv\Scripts\python.exe -m portfolio_backtest.cli --replay reports/runs/my-backtest-suite/baseline--overnight_gap--cppi.json
```

Settings: [config/backtest.json](config/backtest.json).
[Execution contract and limits](docs/BACKTESTING.md),
[acceptance evidence](docs/PHASE3_ACCEPTANCE.md),
[synthetic comparison](reports/phase3-comparison.md).
This is a single-risky-instrument, long-only daily engine, not yet a multi-asset
or live trading system. Today's downloaded market histories are not backdated
to pass historical availability checks. The newer phase-4 checkpoint follows below.


## Phase 4 Black-Litterman equity baseline (0.6.0)

Locally accepted: 184 tests, published numeric example, 12 covariance/view
comparisons plus 3 monthly rebalance cases, with 15 exact replays. Includes
point-in-time universe/return/view contracts, sample/EWMA/Ledoit-Wolf covariance,
prior/posterior, long-only constrained weights, contribution-aware bands and
post-cost CPPI/TIPP budget enforcement. No new dependencies or subscriptions.

```powershell
.\.venv\Scripts\python.exe -m portfolio_equity.cli --suite reports/runs/my-phase4-suite
.\.venv\Scripts\python.exe -m portfolio_equity.cli --input config/examples/equity-synthetic-request.json --output reports/my-equity-allocation.json
.\.venv\Scripts\python.exe -m portfolio_equity.cli --replay reports/my-equity-allocation.json
```

[Configuration](config/equity.json), [model and integration contract](docs/BLACK_LITTERMAN.md),
[acceptance](docs/PHASE4_ACCEPTANCE.md), [comparison](reports/phase4-comparison.md).
The included universe/opinions are synthetic fixtures; numerical correctness is
not evidence of historical profitability. Systematic view generation remains
phase 5. Phase-1/phase-3 financial engines are unchanged.


## Phase 5: systematic equity views (0.7.0)

Price factors -> normalized scores -> chronological fitted relative view ->
uncertainty -> constrained Black-Litterman allocation. Every result retains
its raw inputs, timestamps, settings and model identity. Insufficient model
information produces NO_VIEW. This is a synthetic-tested research baseline.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m portfolio_factors.systematic_cli --suite reports/runs/my-phase5-suite
.\.venv\Scripts\python.exe -m portfolio_factors.systematic_cli --replay reports/runs/my-phase5-suite/fold-150.json
```

Use a new output directory for each suite. Configuration:
[systematic_views.json](config/systematic_views.json). Contract and commands:
[SYSTEMATIC_VIEWS.md](docs/SYSTEMATIC_VIEWS.md). Equations and sources:
[MODELS.md](docs/MODELS.md). Acceptance: [PHASE5_ACCEPTANCE.md](docs/PHASE5_ACCEPTANCE.md).
Next-session context: [SESSION_HANDOFF.md](docs/SESSION_HANDOFF.md).


## Phase 6: EUR/USD research baseline (0.8.0)

Free 30m OHLC capture, closed 1H/4H/D alignment, trend, mean-reversion,
policy-rate differential and NO_TRADE. Signals retain inputs and timestamps;
research backtests include signed exposure, delayed fills, costs, carry and
safe income. Initial plans are non-executable pending phase-7 risk sizing.

```powershell
.\.venv\Scripts\python.exe -m portfolio_fx.cli --suite reports/runs/my-fx-suite
.\.venv\Scripts\python.exe -m portfolio_fx.cli --replay reports/runs/my-fx-suite/fold-1--trend--base.json
.\.venv\Scripts\python.exe -m portfolio_fx.cli --capture data/raw/my-fx-capture --days 30
```

Settings: [fx.json](config/fx.json). [Contract, assumptions and commands](docs/FX_BASELINE.md).
[Acceptance and live-source limitations](docs/PHASE6_ACCEPTANCE.md).
Yahoo and FRED acquisition were verified after the 0.8.1 transport correction.
Missing data still disables the relevant proposal. Performance evidence remains synthetic.


## Phase 7: FX volatility and risk (0.9.0)

Historical/EWMA/GARCH variance, volatility-based stops, cost/carry-aware quantity,
independent capacity limits, take-profit and time exits. 269 tests pass; 22
chronological/stress cases replay exactly. The gap stress retains a budget breach,
so a stop is not represented as a guaranteed maximum loss. Plans remain research-only.

```powershell
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --suite reports/runs/my-risk-suite
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --replay reports/runs/my-risk-suite/fold-1--trend--garch--base.json
```

[Risk contract and equations](docs/FX_RISK.md), [configuration](config/fx_risk.json),
[acceptance evidence](docs/PHASE7_ACCEPTANCE.md), [session handoff](docs/SESSION_HANDOFF.md).


## Phase 8 — FX regimes (0.10.0)

Transparent trend/volatility rules and a Gaussian HMM challenger now annotate
FX decisions using only information available at each timestamp. Saved records
include probabilities, training inputs and exact replay. Regime attribution
measures the existing risk engine after costs and carry; risk limits stay intact.

See [contract and commands](docs/FX_REGIMES.md),
[acceptance](docs/PHASE8_ACCEPTANCE.md) and [comparison](reports/phase8-comparison.md).
292 tests pass; 15 cases across three chronological synthetic holdouts replay
exactly. This validates engineering, not market profitability.

```powershell
.\.venv\Scripts\python.exe config/examples/fx_regime_request.py
.\.venv\Scripts\portfolio-regimes.exe --input reports/runs/regime-request.json --output reports/runs/my-regimes.json
.\.venv\Scripts\portfolio-regimes.exe --replay reports/runs/my-regimes.json
```

Output files are create-only; choose a new name on subsequent runs.
Phase 9 has not started.


## Phase 9 — econometric models (0.11.0)

AR(1), lagged-exogenous ARIMAX(1,0,0), VAR(1), time-varying Kalman coefficients
and Gaussian Markov-switching means share one rolling chronological interface,
with no-change/momentum controls and independent phase-7 risk constraints.
Unstable fits abstain automatically. VECM remains disabled pending economic and
cointegration evidence. All models remain research challengers.

[Contract and commands](docs/ECONOMETRICS.md),
[acceptance](docs/PHASE9_ACCEPTANCE.md), [comparison](reports/phase9-comparison.md).
318 tests; 24 chronological cases and six rejection/disabled cases reproduce
exactly. Evidence is synthetic, not proof of profitable market forecasts.

```powershell
.\.venv\Scripts\python.exe config/examples/econometric_request.py
.\.venv\Scripts\portfolio-econometrics.exe --input reports/runs/econometric-request.json --kind forecast --output reports/runs/my-econometric-forecast.json
.\.venv\Scripts\portfolio-econometrics.exe --replay reports/runs/my-econometric-forecast.json
```

Outputs are create-only. Phase 10 has not started.
