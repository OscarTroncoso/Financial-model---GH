# Phase 4: Black-Litterman equity baseline

## Scope and interfaces

`portfolio_equity` computes strategic equity-sleeve weights. It does not generate
systematic views (phase 5), choose stocks for the user, forecast trade entry
points or send orders. The illustrative universe contains SYNTH_A and SYNTH_B;
these are synthetic labels, not investment recommendations. The separate
published eight-asset fixture verifies the mathematics and is not the production
investable universe. Some of its assets are bonds by design of the source paper.

`Universe` pins ordered asset IDs, account currency, reference weights, their
availability and provenance. Reference weights may be market-cap weights or an
explicitly chosen benchmark; example weights are the latter. The module does
not label chosen weights as observed market capitalization. A historical
universe must include point-in-time membership; today's constituents are not
silently used for old decisions.

`ReturnRow` contains daily arithmetic excess returns relative to the chosen
safe benchmark, observation/availability times and source. `View` contains an
ID, ordered pick vector, annual excess opinion, confidence, availability and
source. Absolute views select one asset; relative baskets have long weights
summing to one and short weights summing to minus one. All timestamps normalize
to UTC. All assets must be represented in the same account currency.

`allocate` excludes unavailable returns before selecting the trailing window.
It rejects insufficient, stale, duplicate, out-of-order or non-daily/gapped
history. It also rejects unavailable universe weights, future/stale views,
invalid dimensions, infeasible constraints and singular/ill-conditioned risk
matrices. There is no undocumented diagonal jitter or pseudoinverse fallback.
A failed computation produces no allocation bundle or order.

## Data foundation connection

`returns_from_prices` consumes phase-2 `Datum` series after the caller selects
explicit snapshot IDs/revisions with `DataLake.as_of`. It requires identical
session timestamps and same-currency adjusted-close series, including an
explicit safe-price series. It calculates price-ratio simple returns and
subtracts the safe simple return. No filling or currency conversion occurs.
Availability is the latest availability of both endpoints of every input.
An ETF safe proxy is a chosen benchmark, not a claim that its return is riskless.

Today's downloaded history can inform a decision today if fresh enough. It
cannot establish what a historical decision knew. Corporate-action revisions
and historical universe membership remain subject to phase-2 vintage limits.
The bridge produces covariance inputs, not executable OHLC bars. No paid data
subscription or additional dependency is required by this phase.

## Financial choices

Exact formulas, dimensions, source locations and hand tests are in MODELS.md.
All means and view values are **annual arithmetic excess returns** as decimal
fractions. Covariances are daily excess-return covariance multiplied by the
configured number of periods per year; this scaling assumes negligible serial
covariance and is not a compounded return forecast. Tau is dimensionless;
Omega has the same squared-return units as tau*Sigma.

The three estimators are centered sample covariance (n-1), zero-mean RiskMetrics
EWMA with causal first-outer-product initialization, and centered spherical
Ledoit-Wolf shrinkage. The selected LW estimator shrinks toward average variance
times identity. It is not the constant-correlation estimator in the separate
'Honey, I Shrunk the Sample Covariance Matrix' paper. The default is LW;
EWMA lambda, sample window, annualization, tau and risk aversion are configuration.

The posterior returns both uncertainty of the mean M and predictive covariance
Sigma+M. The constrained baseline deliberately optimizes with estimated Sigma,
matching the risk-matrix choice of Idzorek's worked example. It never confuses
M with asset-return risk. No views returns the prior exactly.

Confidence uses an explicit single-view Gaussian interpolation convention:
omega=((1-c)/c)*tau*p*Sigma*p'. At c=.5 this is the scaled-view-variance baseline
described in Idzorek's equation 8. For one view, the posterior view mean moves
exactly c of the way from prior to opinion. With interacting views this does
not guarantee an independent percentage tilt for each view, and it is not
claimed to reproduce Idzorek's numerical confidence-calibration procedure.
Zero-confidence views are omitted; full-confidence views are exact observations
and dependent hard views are rejected if the conditioning system is singular.

## Constraints and cash allocation

The optimizer maximizes annual mean-variance utility with weights summing to
one, no shorts, and configurable maximum weight per equity asset. These are
**within-sleeve** weights. It uses projected gradient and a convex objective-gap
certificate. The tolerance is measured in utility, not a guaranteed number of
decimal places in each weight; nonconvergence fails closed.

CPPI/TIPP supplies the overall risky budget. The configured equity share of it
(default 75%) is the equity capacity; unused FX capacity stays safe. A good BL
opinion cannot enlarge this hard budget. No stock selection, sector constraints
or leverage optimization is silently implied by the baseline asset caps.

`schedule` is the monthly ledger adapter: it adds the explicitly supplied
contribution before evaluating drift, records the resulting targets and queues
an order only outside the configured band. The caller persists the latest
monthly decision even if no trade is queued. Ordinary decisions use UTC calendar
months. An explicit emergency input may liquidate between months; BL views do
not generate tactical exits. Updating a model is distinct from rebalancing.

`execute` requires a later timestamp and an account marked to execution prices.
It rechecks the current CPPI/TIPP budget after gaps and **after costs** using a
monotone self-financing equation. This is a multi-asset monetary ledger adapter,
not a replacement for phase-3 OHLC stop/limit execution. Upstream execution
supplies observed marks and safe returns; the adapter does not invent them.
The existing single-risky-instrument phase-3 simulator remains unchanged.

Commission, half-spread and slippage are explicit proportional reference-value
costs using the same convention as phase 3. Net target trades use available
cash to close underweights before selling; there is no liquidate-and-rebuy
round trip. The mean-variance objective itself has no hidden transaction-cost
penalty: bands and the execution ledger handle turnover and realized costs.
No claim of globally minimal turnover, share-lot rounding, taxes or broker fee
replication is made.

## Audit, commands and boundaries

Every bundle saves the exact return rows, universe/benchmark vintage, view
sources, configuration, prior, P/Q/Omega, both posterior covariance meanings,
optimizer weights/certificate, contribution decision, plan and optional delayed
execution ledger. A source hash, runtime versions and payload checksum support
exact replay. Only installed code executes during replay.

```powershell
.\.venv\Scripts\python.exe -m portfolio_equity.cli --suite reports/runs/my-phase4-suite
.\.venv\Scripts\python.exe -m portfolio_equity.cli --input config/examples/equity-synthetic-request.json --output reports/my-equity-allocation.json
.\.venv\Scripts\python.exe -m portfolio_equity.cli --replay reports/my-equity-allocation.json
```

Configuration: `config/equity.json`. Output locations must be new. The input
example is entirely synthetic and includes optional future **execution marks**;
these are not passed to the decision computation. Omit `execution` to save an
allocation and plan without a hypothetical fill.

The suite compares three estimators and four view settings and saves a monthly
accounting sequence. That sequence uses flat execution marks to isolate flows
and costs; it is expressly not a historical performance backtest. Financial
acceptance is based on the published numeric example, hand-ledger tests and
causality/constraint checks. Walk-forward performance research requires a real
universe, certified inputs and the phase-5 view methodology; none is claimed.
