# Model and equation verification register

User requirement, 2026-09-23: use correct, sourced models, never invent missing
formulas. A source citation alone is not economic validation. Preserve the
published model, label implementation conventions, and require hand examples.

## Enabled core

**CPPI allocation**: C=max(V-F,0), E=min(m*C, cap*V). Black & Perold (1992),
*Theory of constant proportion portfolio insurance*, DOI
https://doi.org/10.1016/0165-1889(92)90043-E (publisher abstract checked:
https://www.sciencedirect.com/science/article/pii/016518899290043E).
The exposure is a constant multiple of wealth above a floor, with borrowing
constraints. Our cap<=1 disallows leverage. The nominal contributed-capital floor
is explicitly a project convention, not a claim to replicate their full model.

**TIPP floor**: F=alpha*HWM, equivalently max(previous floor,alpha*V) without
external flows. Original reference Estep & Kritzman (1988), *TIPP: Insurance
without complexity*, https://doi.org/10.3905/jpm.1988.409172. Original full text
was inaccessible; accessible published formulation cross-checked in Dangl, Randl
& Zechner, *Risk Control in Asset Management: Motives and Concepts*, section 3.2.4:
https://link.springer.com/chapter/10.1007/978-3-319-09114-3_14 .
This implements the documented rolling-floor rule, not a full paper replication.
A drawdown floor with alpha=1-d is exactly the same algebraic rule. Continuous
protection assumptions do not apply to monthly trading with delayed fills.

**Cash flows / returns**: time-weighted subperiod returns are geometrically linked.
See CFA Institute GIPS Handbook, provision 2.A.24:
https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/ .
For each period: gross=marked_NAV/prior_NAV; add contribution; apply trade costs;
net growth=gross*(post_cost_NAV/post_contribution_NAV). This is derived by valuing
immediately before/after the external flow. No GIPS compliance claim is made.

**Realized volatility**: sample standard deviation (n-1), multiplied by sqrt(A)
for A assumed equally spaced market periods/year. Definition cross-checked:
https://statproofbook.github.io/D/std-samp.html . Scaling is a convention with
uncorrelated equal-variance increments; it is not a predictive GARCH model.

## Enabled additional challenger: conditional_cppi

Ben Ameur/Prigent (2006), positive-cushion quantile constraint, is implemented
with an explicitly separate rolling Gaussian baseline. See
[CONDITIONAL_CPPI.md](CONDITIONAL_CPPI.md) for equation, units, test cases and
limitations. This is not an alias for any of the dynamic models below, nor a
calibrated protection probability. Version 0.2.0 records the full multiplier
estimate in each audit event. [EPPI_REVIEW.md](EPPI_REVIEW.md) records the
EPPI formulation decision.

## Dynamic research baselines enabled in 0.3.0

Exact formulas, source access, derivations, policy distinctions and tests:
[DYNAMIC_MODELS.md](DYNAMIC_MODELS.md).

- `volatility_adaptive`: normalized inverse-volatility dependence, elasticity 1.
- `adaptive`: V4 project composition of the preceding rule and the reciprocal
  relative risk-aversion factor from Nystrup et al. (2019); neutral regime hook.
- `eppi`: discrete Mancinelli-Oliva (2023) equations 8/11; not the unavailable
  Lee (2008) original, not an exponential function of cushion.

Unverified alternatives (arbitrary elasticity, non-neutral regime predictor,
original-2008 EPPI claim) remain unavailable. Enabling the named variants is not
promotion to live use or acceptance of their empirical usefulness.

## Sharpe and expected shortfall

`sharpe_vs_safe = mean(r_portfolio-r_safe)/sample_std(r_portfolio-r_safe)*sqrt(A)`.
Sharpe (1994), author copy: https://web.stanford.edu/~wfsharpe/art/sr/sr.htm .
This uses observed defensive returns; zero differential variance is undefined.
Absolute differences <=1e-15 are treated as floating cancellation noise, so
an all-safe portfolio cannot obtain a spurious Sharpe from rounding alone.
Square-root annualization assumes uncorrelated periods; a synthetic diagnostic.

Expected shortfall is the mean of the worst `1-confidence` probability mass of
losses `-r`, including the fractional boundary observation, not all tied values
above a sample threshold. Rockafellar/Uryasev (2002), discrete distributions:
https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf .
Default confidence .95 is configurable. ES is per observation, not annualized;
it may be negative for uniformly positive returns. Hand tests include ties and
1.5-observation tail mass. No fitted tail model or risk forecast is claimed.

## Project conventions (not published predictive models)

Nominal floor, contribution-adjusted HWM, monthly schedule, execution delay,
proportional costs and emergency full liquidation are explicitly documented in
IMPLEMENTATION.md. They are testable accounting/risk policies, not assertions of
optimality. Benchmark is monthly constant-mix on an aggregate risky proxy.
Metrics are arithmetic definitions documented in metrics.py. No learned model,
forecasting skill, historical performance or calibration is claimed.

## Promotion gate

Before enabling a blocked model: obtain the exact equation and definitions from
an accessible primary publication, reconcile units/indexes and specification,
record justified implementation changes, hand-calculate examples and limiting
cases, add causality/cost tests, then run the mandatory comparison. Phase 1 acceptance evidence is recorded separately in PHASE1_ACCEPTANCE.md.

## Source catalog

See [REFERENCES.md](REFERENCES.md) for 22 references, access limitations,
machine-readable metadata and equation-to-test traceability. The conditional-multiplier paper now supports a separately named challenger;
the inverse-volatility normalization has its own explicit derivation and policy notes.


## Phase 3 execution and vectorized accounting (project derivations)

Source semantics: SEC Types of Orders and Stop Order (links and exact scope in
BACKTESTING.md). These are accounting identities and declared simulation
conventions, not new published financial models. CPPI/TIPP reuse the verified
phase-1 functions without changing their accepted harness.

Let R be risky reference value, V total pre-trade NAV, w the target fraction,
k=(commission+half-spread+slippage)/10000, and s=+1 for a buy, -1 for a sale.
Solve E=w*(V-k*abs(E-R)) to obtain E=w*(V+s*k*R)/(1+s*k*w).
Units traded=(E-R)/reference_price; safe=V-E-k*abs(E-R).
Example V=1000, R=0, w=1, each cost=100bps: k=.03, E=1000/1.03,
units=1000/103 at reference 100. Execution is 102 and commission is 1 per
unit. Units*102 + commission=1000; NAV+all costs=1000.

Overnight safe income=cash_previous_close*r_safe; signed carry debit=
units_previous_close*price_previous_close*carry_rate. Example cash=500,
risky=500, r_safe=.02, carry=.01: NAV becomes1005 if prices do not change.
These rates refer only to close-to-open; intraday accrual is zero by convention.

Contribution c arrives after closing return: g=pre_deposit_NAV/previous_NAV,
wealth_t=wealth_(t-1)*g, NAV_t=pre_deposit_NAV+c.
HWM_t=max(HWM_(t-1)+c, NAV_t). A flat1000 account plus100 contribution has
NAV1100, TWR0, drawdown0. Maximum drawdown=max(1-wealth/running_peak).

Vectorized daily targets: w_t=target_(t-1), with w_0=0. Define intraday
q_t=close_t/open_t. Previous closing risky fraction is
u_t=w_(t-1)*q_(t-1)/(1-w_(t-1)+w_(t-1)*q_(t-1)), u_0=0.
Let overnight g_t=open_t/close_(t-1). Pre-open NAV factor is
A=u*g+(1-u)*(1+r_safe), risky fraction v=u*g/A.
After-cost factor B=(1+s*k*v)/(1+s*k*w), s=sign(w-v) (zero uses +1).
Period NAV factor=A*B*(1-w+w*q); cumulative NAV=initial*product(factors).
Cost=previous_NAV*A*k*abs(w*B-v). All prices positive; depleted NAV rejected.
This screening formula excludes flows, exits and carry; event parity is tested.

Stops: entry100, stop10%, next open70 implies exit70 and a1000 fully invested
account becomes700, not900. If one candle touches90 and110, stop-first gives900.
A take-profit110 with1% sell impact requires reference>=110/.99; a mere110
high is insufficient. Time stop2 counts entry bar and next bar, then fills at
following open. See tests/test_backtest.py for these and cost/flow/gap examples.
