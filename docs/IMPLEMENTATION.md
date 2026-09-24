# Phase 0 / Phase 1 implementation contract

The specification and roadmap remain authoritative. This file records explicit
first-implementation choices where they leave research questions open.

## Phase 0

Python 3.12+, standard-library runtime and unittest; build backend pinned in
pyproject.toml. Configuration lives in config/lab.json with the typed, validated
schema in portfolio_lab.config.LabConfig. No broker, credentials or live orders.
The package separates financial rules, accounting, simulation, metrics and audit.

## Phase 1 conventions

- EUR monetary amounts and decimal simple returns, float64/Python float research
  arithmetic, no lot rounding or taxes. Long-only, no borrowing, zero financing
  expense by construction. Safe series is net of fund fees; not guaranteed cash.
- Each observation closes one market period. Its return is earned by holdings
  already present. Contributions are added after returns; previous decisions then execute at that close with explicit
  one-way commission + half-spread + slippage. This one-observation delay exposes
  ordinary and emergency decisions to gaps. It is not an intraday fill model.
- First observation is a zero-return inception snapshot, initially all safe.
  Initial allocation is queued and executes at the next observation. No extra
  monthly contribution at inception. Thereafter the first supplied observation
  on/after rebalance_day each month adds the contribution before deciding targets.
  Missing complete months are rejected rather than silently skipping deposits.
- CPPI capital floor = protected_fraction * cumulative contributed capital;
  nominal, no discounting or safe-rate accrual. TIPP uses a monetary HWM shifted
  upwards by each contribution before comparison with current NAV. This protects
  new capital without interpreting it as investment performance. Daily or monthly
  ratchet is configurable; contribution adjustments always apply immediately.
- Drawdown floor shares the TIPP function with alpha = 1 - max_drawdown. Pure
  classical CPPI always uses capital floor; pure TIPP always uses TIPP floor.
  run(..., model=None) selects the configured floor policy. Explicit comparison
  model names override it. HWM tracks daily even when the floor ratchets monthly;
  the monthly floor uses the highest observed value, including interim peaks.
- Performance drawdown and returns use a contribution-neutral wealth index;
  protection distance uses actual monetary NAV and floor. These are distinct.
- Realized volatility uses sample standard deviation of trailing observed daily
  risky returns, annualized by sqrt(periods_per_year). Zero-return inception is
  excluded. No observation after the decision timestamp is accessible. Volatility
  is reported as unavailable during warm-up; unknown/unverified variants cannot be run. Calendar safe fallback uses
  (1 + annual_net_return) ** (elapsed_calendar_days / 365) - 1.
- Dynamic variants are defined in DYNAMIC_MODELS.md, including explicit source
  identities, project compositions and numerical/domain policies.
- Static benchmark uses 1 - reference_safe against an aggregate risky proxy.
  All lab strategies use that same proxy. The 75/25 split is reported as reference
  equity/FX capacity only; no actual equity or FX sleeve integration in phase 1.
- Ordinary target trades use a NAV drift band. Net buying/selling is computed
  from current holdings after deposits; no liquidation/rebuy cycle. Emergency
  actions ignore the band and only reduce exposure. Floor proximity, drawdown,
  critical volatility, a hard exposure-cap breach or excess exposure trigger
  full exit in the first rule.
  Static benchmark has no insurance emergency overlay for a transparent baseline.
- Pending buys are cancelled if a newly observed emergency is present; no new
  emergency fill is assumed at the same close. Hard-cap repair may sell during
  a queued execution. Prices can breach limits between observations/executions.
- All inputs/configuration, code hash, algorithm version and daily audit events
  are saved with report artifacts. Invalid/future/nonfinite data aborts the run;
  no partial actionable result is returned. State is valued just before execution
  for HWM purposes, so transaction costs cannot erase an already observed peak. No live data update exists yet.

## Open questions / limits

Defaults are illustrative, not fitted. Floor level, multiplier, exposure limits,
emergency thresholds, EPPI mapping and costs require later research. Synthetic
stress paths verify mechanics; they do not validate historical or OOS performance.
Phase 1 has a small daily simulation harness, not the phase-3 general execution
engine. Real market calendars, intraday gaps, instrument liquidity, lot sizes,
FX carry and a full multi-sleeve implementation belong to later phases.

## Planned validation

Hand examples for floors, HWM, cushion, multiplier composition, safe
returns, net trades/costs and performance metrics. Integration checks for timing,
monthly deposits, monitoring without trading, delayed emergency fills, shocks,
causality (altering future data preserves earlier results), and reproducibility.

Reserved configuration fields for multiplier volatility/adaptation do not enable
those models. They are not used by CPPI/TIPP baselines. Invalid data aborts a run;
this is not a live recovery policy. Observations must be daily, with at most seven
calendar days between rows; no exchange calendar or missing-session inference.


## Version 0.2.0 addition

`conditional_cppi` is an additional sourced quantile-bound challenger with a
rolling Gaussian estimator; see CONDITIONAL_CPPI.md. It uses the configured
floor policy, holds safe during warm-up, and preserves monthly execution timing.
Its estimator inputs are risky returns relative to safe returns, its log mean
is fixed at zero and its risk horizon is configurable. A non-ready estimate
cannot authorize purchases; unusable risk states request a delayed exit even
with optional emergencies disabled. A pending buy exceeding the current
pre-cost quantile budget is cancelled. No other enabled strategy is changed.


## Version 0.3.0 additions

The three remaining research benchmarks now use the exact identities in
DYNAMIC_MODELS.md. Dynamic estimators record their factors/raw state. Adaptive
uses pre-fill net wealth drawdown for buy veto and post-cost drawdown for the
next decision. This preserves causality and includes trade costs in risk state.
EPPI raw state starts at its own eta, independent of the fixed CPPI multiplier.

Sharpe is measured against each actual safe return; expected shortfall uses
fractional tail mass and configurable confidence. Both are diagnostic metrics.
The validation CLI runs fixed sensitivity profiles, saves all inputs/events,
and replays every bundle before writing validation.json. An incomplete suite
has no successful validation.json. All values and profiles remain research
choices, not optimal settings or out-of-sample evidence.
