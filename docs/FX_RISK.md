# FX volatility and risk — phase 7, package 0.9.0

## Scope and model identities

`portfolio_fx_risk` consumes the existing causal EUR/USD data and directional
signals. It adds volatility, a stop-distance interface, constrained quantity,
TP/time exits and a separate risk-sized research ledger. The phase-6 engine
remains an unchanged comparison baseline. Earlier saved experiments continue
to replay with their corresponding source. Portfolio-wide allocation/IBKR and
regime inference remain later roadmap tasks.

Default parameters are in config/fx_risk.json. Every coefficient and bound is
illustrative, not claimed optimal. The source-verified equations, derivations
and hand cases are in MODELS.md.

- `realized`: rolling sample standard deviation of log returns (ddof=1),
  explicitly historical sample volatility, not high-frequency integrated RV.
- `ewma`: zero-mean RiskMetrics scalar variance recursion. Initialize with the
  first configured seed window's mean squared return, then update using each
  subsequent known return. A default .94 at 4H is a research setting; the
  publication's daily calibration is not transplanted as empirical evidence.
- `garch`: stationary zero-mean GARCH(1,1). Omega uses variance targeting;
  alpha/beta minimize Gaussian quasi-likelihood over a finite configured grid.
  Initialization and scoring are explicit. This restricted estimator is
  deterministic, not a full continuous MLE. Audit includes every candidate,
  scores, selected parameters and fitted window. No optimality outside the
  grid, distributional calibration or economic superiority is asserted.

Window defaults: 60 returns, seed 12, from 61 completed 4H closes, filtered by
actual availability. Variance units are squared log return per observed 4H
bar. Weekend close-to-close gaps remain part of the next observed return;
this is a trading-bar series, not equally spaced wall-clock observations.
Missing/partial 4H buckets are not synthesized. Freshness and maximum historical
gap guards apply. Flat/degenerate data gives NO_TRADE, not unlimited leverage.

## Stop and quantity policy

First choose D=max(min_pips*.0001, entry*k*sigma*sqrt(H)), then size.
This is an explicit linearized volatility stop rule, not a coverage probability
or VaR guarantee. H is a configurable stop-distance scaling horizon: for H>1,
frozen forecast variance is a policy approximation, not GARCH's exact
multi-step conditional forecast. Default H=1. Excessive distances are rejected,
not clipped; there is no fixed 5%-price stop. The configurable minimum is 5
pips, which is a price increment and not 5%.

For direction d=+1/-1: stop=S-d*D and target=S+d*R*D. R is a gross price-distance
reward multiple, not expected value or a net-of-cost win probability. Barriers
anchor to the actual entry reference price, retaining the decision's distance.
Large entry-price drift cancels the candidate. Recomputed quantity at execution
can only reduce the original proposal.

Risk amount is FX capital * risk_per_trade, further bounded by remaining
portfolio risk. Caller supplies USD NAV, FX capital, existing open risk,
notional, used margin and position count via Capacity. The CLI's convenience
capture mode explicitly assumes a flat account and requires NAV/FX capital;
non-flat callers must use the Python API with complete account capacity.

Conservative per-unit modeled loss includes D, both-side reference-notional
costs, and an adverse carry reserve to the time limit. The exit-notional bound
uses S+max(1,R)*D. Quantity is the minimum of risk, post-entry-cost portfolio
risk, absolute/portfolio notional, free-margin/leverage and maximum-unit bounds.
Round down to the configured increment; below minimum size is NO_TRADE.
The kill switch and maximum concurrent-position limit are independent of the
signal and volatility model. Neither a larger forecast nor a smaller variance
can bypass them. Equity/FX portfolio integration is still phase 14; supplied
capacity must ultimately come from that hard allocation layer.

## Execution contract and unavoidable gaps

Account currency remains USD, with the phase-6 collateralized linear EUR/USD
contract, commissions, half-spread, adverse slippage, ACT/365 safe income and
separate signed carry. This is not physical spot settlement or an IBKR model.
The phase-6 `exposure_fraction` is unused by the risk engine: quantity is set by
the risk calculation and caller-provided FX capital fraction in the experiment.

Signals use completed 4H data and cannot fill at an open coincident with their
decision. At execution, account/cost/capacity checks run again. One net EUR/USD
position is simulated; a reversal closes before opening the other direction.
A same-direction signal holds existing units and does not widen its stop.

At an observed open, resting gap barriers have priority, then expired holding
horizon and hard notional/kill limits, before any pending signal. Gap stops
fill at the adverse observed open. Gap TPs receive the target reference price,
with no favorable price improvement. A protective exit cancels a pending entry
and prevents same-bar re-entry. The next scheduled decision may propose anew.

Within a candle, if both barriers touch, stop wins. Otherwise fill the touched
barrier. Intrabar event time is conservatively the close, accruing the full
bar's carry. A precommitted time stop closes at its aligned 30m deadline (or
first available mark after a closure/gap). Maximum holding time must be a
multiple of 30 minutes. Resting barriers precede the time stop. Final holdout
liquidation remains precommitted.

Without an adverse gap, extra delay, or worse-than-configured costs/carry,
modeled stop loss stays within its configured budget. The reserve is not a
maximum possible loss: weekend gaps and delayed time exits can exceed it.
Reports retain actual budget violations, including an intentionally adverse
3% price-gap stress. Safe-asset losses are separate from FX trade risk.

## Audit, validation and evidence limits

Each plan saves the directional signal, volatility input bars and their raw
candles, fitted parameters, stop, target, sizing caps, risk/cost configuration,
account capacity, decision time and source identity. Bundles additionally save
the full request/runtime and regenerate the result on replay. Both valid and
NO_TRADE requests can be reproduced. All plans remain `executable=false` for
brokerage: a complete risk plan is not authorization for live trading.

Chronological synthetic comparisons evaluate realized/EWMA/GARCH with the
same trend rule, plus mean-reversion, macro and flat controls and an elevated
cost case. Later squared returns are attached only to completed runs as noisy
variance proxies (QLIKE and MSE). No random split, test-based hyperparameter
selection or automatic model promotion occurs. Three holdouts plus a gap
stress verify both baseline accounting and stop limitations; no market edge
is established. Real current-data proposals do not create historical vintages.

## Commands

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --suite reports/runs/new-risk-suite
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --replay reports/runs/new-risk-suite/fold-1--trend--realized--base.json
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --capture data/raw/my-fx-capture/normalized.json --nav-usd 10000 --fx-capital-usd 1000 --output reports/runs/new-risk-proposal.json
.\.venv\Scripts\python.exe -m portfolio_fx_risk.cli --replay reports/runs/new-risk-proposal.json
```

Capture remains the phase-6 portfolio_fx.cli command. Optional `--at` fixes
as-of time; `--config` selects the risk settings. `--input request.json --output
result.json` runs explicit research requests; a suite bundle's payload.request
is a complete example. Suite fixtures explicitly record settings and never
silently read production configuration. Existing outputs are not overwritten.
