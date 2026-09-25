# Econometric model zoo — phase 9

Package `portfolio_econometrics`, distribution 0.11.0. Specification §20.1,
roadmap phase 9. All models are research challengers; no live promotion.

## Implemented scope

| Name | Exact implementation |
|---|---|
| no_change | Forecast zero next-bar log return; no-position control |
| momentum | Forecast the latest completed log return |
| ar | OLS AR(1) with intercept on log returns |
| arimax | ARX(1): ARIMA(1,0,0) specialization with a known lagged macro predictor; no MA terms or general order search |
| var | Bivariate OLS VAR(1): FX log return and change in policy-rate differential |
| kalman | Time-varying intercept and AR(1) coefficient, random-walk states, configured Q/R and Kalman filtering |
| markov_switching | Gaussian Markov-switching mean and variance, autoregressive order zero; not a replication of Hamilton's AR(4) |
| vecm | DISABLED: no approved economic relationship and cointegration evidence |

ARIMAX and VAR use the same regressors for their first equation, so their
one-step FX forecasts can coincide. VAR additionally estimates the second
equation and joint covariance and checks the full transition spectrum. This
is expected mathematics, not an assertion of two independent signals.

The existing phase-6 direction rules and phase-7 risk package are retained.
Optional higher AR/MA orders and hyperparameter searches are not claimed.
VECM cannot be enabled by setting a flag; its prerequisites need separate
research, evidence and implementation. No phase-10 ML or ensembles were added.

## Shared information and evaluation contract

Target: next observed complete UTC 4H close-to-close log return. Every decision
uses only available 30m vintages and complete aggregate candles. Default rolling
window: 60 returns from 61 closes. At each decision every estimator refits on
its current historical window, then forecasts one new observation. Earlier
holdout observations may become training data only after they are observed.
There is no random split, future target in a training pair, or holdout tuning.
Orders and numerical limits are fixed before each run and stored in config.

Models with macro inputs reconstruct EUR and USD policy rates as known at EACH
historical bar, respecting their availability and staleness. x_t is the change
in (EUR policy rate minus USD policy rate). A currently downloaded historical
CSV is not historical publication/ingestion evidence. Constant or missing macro
features are rejected/unavailable, not fabricated or silently removed. These
policy rates remain proxies, not matched market yields or broker carry quotes.

At decision t, ARX trains pairs (r_(s-1), x_(s-1)) -> r_s and forecasts using
(r_t,x_t); it never asks for x_(t+1). VAR likewise forecasts both coordinates
from their known current values. Standardization is fitted only on each known
window; scaling and coefficients are saved. Kalman's stored within-window
coefficient path is fitted training diagnostics, not historical trading labels
computed with the normalization then available at each past date.

Weekend gaps count as one observed-return transition, not an imputed sequence
of missing calendar bars. Maximum gaps and freshness limits are configurable.
The forecast horizon is the next observed bar, potentially after a closure.
A historical trading run requires certified close-time candle availability,
ordered nonoverlapping candles and the existing execution gap guards.

## Rejection and risk

Config: `config/econometrics.json`. Predefined fit gates cover insufficient data,
rank/conditioning, nearly constant features, AR/VAR spectral radius >=.995,
excessive standardized coefficients, Kalman covariance, Markov convergence and
state occupancy, and extreme forecast magnitudes. No clipping disguises an
unstable model. Result status is READY, REJECTED, UNAVAILABLE or DISABLED, with
reason, configuration, input lineage and source identity. Failed forecasts
cannot create a new position; the ledger's existing NO_TRADE handling remains.

The forecast must clear a configured first-order log-return hurdle: estimated
round-trip proportional fees/spread/slippage + buffer + adverse carry reserve
for the maximum holding period. It is a research heuristic, not guaranteed
expected profit. Phase-7 volatility, stops, take-profit, time exit, risk sizing,
post-cost exposure limits and kill switch remain independent of the forecaster.
Changing predictive variance cannot override these limits.

`ledger.py` is an explicit snapshot of the phase-7 ledger with ONLY proposal
dispatch adapted. Tests compare the entire function body and barrier function
with their originals and check no-change accounting numerically. Shared sizing
and volatility functions are imported from phase 7. This preserves old source
identities and replays. Future ledger fixes must update both versions and pass
the parity test; divergence must be deliberate and documented.

## Metrics and governance boundary

Trading metrics use the same USD linear collateral ledger: actual configured
fees, spread, slippage, safe income and signed carry. Barriers may still gap.
A next-bar forecast is not a guaranteed holding time: pending orders execute
at a later observed open; stops and signals can shorten/extend the position.
The unchanged configured maximum holding period is 48 hours by default.

After generating the entire run, scoring attaches later returns whose label
ends do not exceed the holdout end. Metrics: MAE, RMSE, sign accuracy (zero is
its own sign), information coefficient when defined, and error by transparent
regime. The no-change error comparator uses the SAME available label timestamps;
coverage and rejection counts are reported so selective abstention is visible.
These are conditional metrics; different coverage must not be mistaken for an
unconditional performance advantage. Predictive moments are not calibrated
probabilities; no Brier score or Gaussian coverage claim is fabricated.

Entry-decision regime attribution reuses the phase-8 transparent rule and
performance accounting. Safe income stays separate, and grouped net trade P&L
must reconcile with NAV. Markov predictive state probabilities are saved too,
but are not silently equated to the transparent trend/volatility labels.

A completed holdout is rejected for further research if forecast coverage is
below .5 or maximum drawdown exceeds .20 (configurable). This diagnostic uses
the completed holdout, NEVER revises its trades, and is not a live selection or
promotion engine. ELIGIBLE_FOR_FURTHER_RESEARCH does not mean profitable or
approved for capital. Phase 11 governance/ensembles remain out of scope.

## Audit and commands

Each JSON bundle stores the full request, raw candles/rates, forecasts/fits,
proposals, trading ledger, metrics, causal regimes, source identity and runtime.
Replays check integrity and recompute the entire result. Output files are
create-only. NumPy is already pinned; no new dependency is required.

```powershell
.\.venv\Scripts\portfolio-econometrics.exe --suite reports/runs/new-econometric-suite
.\.venv\Scripts\portfolio-econometrics.exe --replay reports/runs/phase9-accepted-20260925/fold-1--ar--base.json
.\.venv\Scripts\python.exe config/examples/econometric_request.py
.\.venv\Scripts\portfolio-econometrics.exe --input reports/runs/econometric-request.json --kind forecast --output reports/runs/my-forecast.json
```

Request schema: common keys `candles`, `rates`, `model`, `econometrics`.
Forecast adds `time`. Proposal adds `time`, `capacity`, `risk`, `volatility`,
`features`, `execution`. Evaluation adds `start`, `end`, `risk`, `volatility`,
`features`, `execution`, `fx_capital_fraction`, `regimes`. These dictionaries use
the existing dataclass schemas; `econometrics` is EconometricConfig and
`regimes` is RegimeConfig. APIs: `forecast`, `propose`, `bundle`, `replay`.

## Research limits

Synthetic acceptance tests prove engineering properties, not market stationarity,
forecast calibration, economic causality or profitable trading. Differencing
and root checks alone do not prove stationarity. Short, fixed windows, one-lag
specifications and a single deterministic Markov initialization are deliberately
simple starting points. Variances exclude model-parameter uncertainty except
Kalman's conditional state uncertainty; Q/R themselves are fixed assumptions.
Longer point-in-time market datasets and robust economic validation remain
necessary before any promotion. FRED's repaired transport is unchanged.
