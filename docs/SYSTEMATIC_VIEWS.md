# Phase 5 — systematic equity views

This phase implements a complete **research baseline** from available prices to
normalized factors, statistically estimated relative views and constrained
Black-Litterman weights. It does not authorize live execution or establish a
profitable strategy. LLM-derived equity features remain later work, as specified
by the roadmap. No phase-6 FX strategy is included.

## Operational path

1. Pin an ordered equity universe, same-currency adjusted-price vintages and an
   explicit safe-price benchmark using phase-2 contracts.
2. At each decision, filter prices by observation and actual availability,
   then choose the latest known revision per observation. Reject ambiguous ties,
   missing sessions, insufficient history, mismatched currencies and stale data.
3. Compute momentum and volatility descriptors. Keep the exact price inputs,
   formula configuration and a content ID for each derived-feature batch.
4. Select the newest known economic observation of each descriptor, then its
   newest available revision. Normalize within the same fixed universe at that
   time, orient the direction, cap extreme scores and form a weighted composite.
5. Associate past snapshots with completed future return labels, retaining all
   label prices and their availability. Labels remain outcomes, not features.
6. Fit an intercept/slope regression for a **fixed pair's score difference**
   against its realized horizon return difference. Use only labels available
   by the decision and ending before the embargo cutoff. Purge overlapping
   label intervals, keep a bounded trailing history and reject stale training.
7. Convert the forecast and uncertainty to one relative Black-Litterman view.
   The phase-4 allocation pipeline consumes the same Sigma/tau and verifies that
   the confidence conversion preserves the intended effective Omega.
8. Save all inputs, selected vintages, scores, labels, coefficients, confidence,
   view and allocation. Checksums, code hashes and exact replay verify the chain.

The fixed pair has a positive and a negative coefficient in P; these labels
indicate a comparison, not a request for a short position. Portfolio weights
remain long-only and constrained. CPPI/TIPP and the phase-4 rebalance ledger
continue to limit overall risky capacity independently of the view.

## Data, factor and model conventions

Production defaults are in `config/systematic_views.json`; normalization alone
is in `config/factors.json`. The SYNTH_A/SYNTH_B pair is explicitly illustrative:
replace it only with a documented investable universe and its as-of inputs.

Momentum is a session-count price-ratio return using a 252-session lookback and
21-session skip. This approximates the familiar prior-month-excluded momentum
idea, but does not replicate French's calendar-month, size-sorted factor.
Volatility is sample standard deviation (n-1) of the latest 63 simple returns,
multiplied by sqrt(252). Descriptors use adjusted-price proxies without adding
dividends twice. The current anchor and all formula dependencies must be known.

The default composite is 60% oriented momentum and 40% inverse-oriented
volatility z-score. Cross-sectional population standard deviation (ddof=0),
clipping at +/-3 and these weights are declared project conventions; they are
not a replication of MSCI's raw winsorization, quality index or weighting rules.
Constant cross-sections get zero scores; missing data are rejected, never zero
filled. All factor inputs must be complete for the fixed universe.

Feature observation is the economic measurement date. Publication, ingestion
and availability are separate instants, with chronological validation. For
internally derived descriptors, calculation at t is modeled only after proving
that every raw input vintage was already available at t. This does not backdate
vendor ingestion. A new revision cannot alter a saved historical snapshot.

The baseline emits one fixed-pair relative opinion, not an independent opinion
for every stock. Multiple forecasts sharing coefficients would generally have
correlated errors; a single view avoids falsely treating them as independent.
Factor groups such as quality or valuation can enter through generic Feature
contracts once their formulas, units and publication vintages are verified;
no invented fundamentals or unverified connectors are supplied in this phase.

## Regression and confidence limits

The score-to-return mapping is fitted, not a hardcoded assertion that one
z-score equals a particular return. See MODELS.md for formulas and hand tests.
OLS assumes a linear relation, independent homoskedastic errors and fixed
predictors. Non-overlapping labels do not prove those assumptions in markets.
The estimated conditional-mean variance is a **plug-in approximation** for
view uncertainty. It is not a calibrated probability of beating another stock,
not a confidence interval's coverage probability, and not the variance of an
individual future return. No market calibration claim is made.

Default label horizon is 21 sessions; annual arithmetic scaling is A/H for the
mean and (A/H)^2 for uncertainty in that mean. This is a declared convention,
not compounding realized annual wealth. Risk covariance uses the same annual
units as the phase-4 model. An annual mean standard-error floor and a confidence
cap (default 0.75) prevent a perfect in-sample fit from becoming a hard view.
A maximum annual forecast magnitude is a risk bound, not a winsorized forecast:
exceeding it returns NO_VIEW. Confidence caps never override portfolio caps.

Other valid NO_VIEW cases: insufficient non-overlapping labels, stale labels,
constant training scores, or current scores outside the training range. In
those cases phase 4 uses its no-view prior. Invalid/tampered data, currencies,
units or risk matrices instead fail closed without producing an allocation.

Training period selection is based on times, never label values: select eligible
known labels, walk backward from the embargo boundary to remove overlap, cap
the count, then fit in chronological order. Sample/feature/code IDs are retained.
There is no random time-series split and no future release in a predictor.

## Commands and saved input format

```powershell
# Complete synthetic walk-forward acceptance, including replay and cost examples
.\.venv\Scripts\python.exe -m portfolio_factors.systematic_cli --suite reports/runs/my-phase5-suite
# Run an explicit as-of market/synthetic request, writing a new bundle
.\.venv\Scripts\python.exe -m portfolio_factors.systematic_cli --input my-request.json --output reports/my-views.json
.\.venv\Scripts\python.exe -m portfolio_factors.systematic_cli --replay reports/my-views.json
# Independently build/replay a normalized descriptor snapshot
.\.venv\Scripts\python.exe -m portfolio_factors.cli --input config/examples/factor-snapshot.json --output reports/my-factors.json
.\.venv\Scripts\python.exe -m portfolio_factors.cli --replay reports/my-factors.json
```

A systematic request has exactly `universe`, `prices` (asset ID -> Datum JSON
rows), `safe_prices` (Datum JSON rows), `decision_time`, and `training_times`.
`Datum.to_dict()` from phase 2 gives the row representation. Future rows may be
present in an experiment file but cannot enter an as-of computation. Conflicting
same-time vintages are rejected. Historical training features use historical
vintages, while completed labels may use revisions already known at fitting time.

The suite writes self-contained fold bundles: `payload.request` is a runnable
example and `payload.settings` records its explicit fixture overrides. Fixture
windows (20/2 momentum, 10 volatility, 5-session labels) differ from production
settings to create a compact deterministic test. The suite never reads or
silently overrides the production config: it is a fixed engineering experiment.

## What the evidence does and does not establish

Six chronological test folds refit using earlier known labels and compare
forecast errors with zero and training-mean baselines. Outcome labels are
attached only after the forecast is saved. The report separately compares
no-view and systematic-view allocation costs, plus an elevated-cost profile,
using the phase-4 delayed monetary ledger and flat execution marks. These cost
examples isolate accounting and turnover; they are not market P&L backtests.

Replay, hand calculations, availability, constraints and traceability satisfy
the phase-5 engineering gates. Real-data walk-forward performance, robustness
to economic regimes, empirically calibrated confidence and promotion to capital
allocation are not established by the synthetic results. They remain explicit
research/governance work, not missing code in this baseline. Actual execution
validation still uses the appropriate event engine and market assumptions.
