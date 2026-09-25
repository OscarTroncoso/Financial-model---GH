# FX regime engine â€” phase 8

Research package `portfolio_regimes`, distribution 0.10.0. Specification Â§19.
The phase-6 directional rules and phase-7 sizing/ledger remain unchanged.
Regimes annotate decisions; they never create an order or override risk limits.

## Inputs and chronology

Use complete UTC 4H bars derived from as-of 30m candles. Returns are natural
log close ratios, dimensionless per observed trading bar. No annualization,
weekend imputation or claim that a weekend return covers exactly four hours.
Each request contains raw candle vintages, decision times, configuration and an
explicit earlier training cutoff on a UTC 4H boundary. Configuration defaults
are in `config/fx_regimes.json`; pass this object in the request's `config`.

Training selects 61 bars available at the cutoff (60 returns). That vintage,
including its final close, stays frozen. Every decision independently selects
only bars available by that decision. Later training corrections cannot refit
the frozen HMM; a new cutoff is required. Within a decision's saved snapshot,
post-cutoff corrections can change filtering of earlier observations; the
`filtered_path` is an as-of reconstruction, NOT replacement historical decision
labels. Attribution always uses the separately saved decision record.

The most recent training bar must end exactly at cutoff. For a Monday holdout,
use the last completed pre-weekend close as cutoff, not Monday midnight. A snapshot downloaded
today cannot be claimed available at historical closes. For such a download,
choose a future training boundary after ingestion and collect later candles
before obtaining an out-of-sample HMM result. Historical evaluation continues
to enforce the phase-7 historical availability contract.

## Transparent baseline

Window: 12 returns. Signed path efficiency is sum(r)/sum(abs(r)), zero on a
constant path. Values >=0.4 are `up`, <=-0.4 `down`, otherwise `sideways`.
Sample standard deviation below .001 is `low`, >=.003 `high`, otherwise
`medium`. All values are configurable project research conventions, not a
claimed published strategy or estimated trading advantage.
Nine combined labels have deterministic one-hot membership, explicitly marked
as such. Sideways does not establish mean reversion; price volatility alone
cannot identify news, events, liquidity stress or a macroeconomic crisis.

## HMM challenger

Gaussian univariate emissions; 2 states by default, optionally 3. Baum-Welch
uses ONLY the completed training window. Center/population-scale are fitted
there, followed by a deterministic EM initialization. The implementation uses
log-domain recursions, a variance floor and a convergence gate. See MODELS.md
for equations, source and implementation policies.

After training, parameters remain frozen and only forward filtering is used.
The first new observation starts from last_training_posterior @ transition.
Each state is named `variance_rank_0`, etc., ordered by training variance and
then mean. Rank zero need not mean low volatility in an absolute sense; ranks
across folds do not imply the same economic regime. Fitted means/variances,
transitions, initialization, likelihood history and scaling are saved.
Probabilities are conditional on this fitted model, not calibrated truth.
EM can find a local optimum; one deterministic initialization is a reproducible
challenger, not evidence of optimal estimation. No model is promoted to trading.

Missing/stale inputs, large gaps, degenerate or nonconverged fits emit UNKNOWN.
Its probability {UNKNOWN:1} is an abstention marker. Invalid schemas/conflicting
vintages raise errors. No failed fit silently substitutes a confident regime.
Rules and HMM abstain independently. No event-calendar classification is claimed.

## Performance attribution

Evaluation embeds and recomputes the exact phase-7 request and ledger. Entry
fills link to their original signal ID (including reversals), then to its
regime at decision time, strictly before entry. Realized completed-trade P&L,
costs, carry, count, expectancy, hit rate and holding time are grouped by that
hard state; probabilities remain in each assignment. This is descriptive
attribution of an unchanged strategy, not a backtest of regime-based routing.

Safe collateral income remains separate. Group trade P&L + safe income must
reconcile with NAV change. No subgroup Sharpe, causal profitability inference
or probability-weighted pseudo-portfolio is reported. Empty groups stay empty;
NO_TRADE has zero trades. Reports remain separated by fold/model/cost profile.

## Commands and request schemas

```powershell
.\.venv\Scripts\python.exe -m portfolio_regimes.cli --suite reports/runs/new-regime-suite
.\.venv\Scripts\python.exe -m portfolio_regimes.cli --replay reports/runs/phase8-accepted-20260925/fold-1--trend--base.json
.\.venv\Scripts\python.exe -m portfolio_regimes.cli --input request.json --kind inference --output reports/runs/regimes.json
.\.venv\Scripts\python.exe -m portfolio_regimes.cli --input evaluation.json --kind evaluation --output reports/runs/regime-evaluation.json
```

Inference request keys: `candles` (phase-6 Candle dictionaries), `times`
(strictly increasing UTC timestamps), `training_cutoff`, `config`.
Evaluation request keys: `risk_request` (phase-7 backtest schema),
`training_cutoff` (no later than holdout start), `config`. Evaluation generates
regimes at every risk decision. Python API: `infer`, `bundle`, `replay`.
See `config/examples/fx_regime_request.py` to build a reproducible request.
All output paths are create-only; replays verify checksum and full recomputation.
Bundles contain code identity, Python/NumPy versions, raw requests, fitted
parameters, state probabilities, input bar lineage and performance assignments.

Optional clustering/GMM and Markov-switching are not implemented in this phase.
The former is optional in the roadmap; the latter belongs to later research.
