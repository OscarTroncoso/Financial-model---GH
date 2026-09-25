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


## Phase 4 — sourced Black-Litterman baseline and execution conventions

Primary sources: Idzorek (2004), equations 1, 2, 3, 8; Figure 1; Tables 5/6,
[author's paper hosted by UPenn](https://www.cis.upenn.edu/~mkearns/finread/idzorek.pdf).
RiskMetrics (1996), section 5.2.1.1, equation 5.6, and Table 5.3 initialization,
[original technical document](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a).
LW spherical target: Ledoit/Wolf (2004), *A well-conditioned estimator*,
DOI 10.1016/S0047-259X(03)00096-4; accessible original software implementation
and API example in [scikit-learn](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/covariance/_shrunk_covariance.py).
The publisher abstract and indexed paper extracts were checked; direct access
to the author's full PDF failed. The centered finite-sample algorithm is verified
against the original scikit-learn implementation and its numeric example,
not claimed as a complete reproduction of all theoretical paper assumptions.
These checks were performed 2026-09-24. Full interface choices: BLACK_LITTERMAN.md.

### Covariance equations

For n daily excess-return rows x_t in R^p, let z_t=x_t-mean(x).
Sample S=sum(z_t*z_t')/(n-1). With [.01,.02],[-.01,0], S has all entries .0002.
Annual covariance=A*S; A=10 makes all entries .002 (unit test).

EWMA H_1=x_1*x_1'; H_t=lambda*H_(t-1)+(1-lambda)*x_t*x_t'.
Mean zero and initialization are explicit choices consistent with the cited
RiskMetrics example. With [.1,.2],[-.1,0] and lambda=.5, final H is
[[.01,.01],[.01,.02]]. Multiply by A. No future seed or forward filling.

LW centered ML S=sum(z_t*z_t')/n; F=tr(S)/p*I; D=||S-F||_F^2.
B=max(0, (mean(||z_t||^4)-||S||_F^2)/n).
Shrinkage rho=min(1,B/D), with rho=0 when D=0. Estimate=(1-rho)S+rho*F.
The 1/p normalization of both B and D in the reference implementation cancels.
With rows [.01,0],[-.01,0],[0,.02],[0,-.02], rho=17/18 and the result is
1e-4*diag(29/24,31/24). scikit-learn's seeded 50-row example gives approximately
.23 shrinkage; ours gives .2302540620023914. Degenerate covariance is not silently
repaired for use by Black-Litterman; it is rejected at the model boundary.

### Prior and posterior

Sigma is positive-definite annual covariance, w_ref sums to one, delta>0.
Pi=delta*Sigma*w_ref. For Sigma=diag(.04,.09), w_ref=(.6,.4), delta=2.5,
Pi=(.06,.09). Selected reference weights need not be asserted to be market caps.

P is k by n, Q is k annual excess opinions, Omega is k by k view-error
covariance. Let C=tau*Sigma, A=P*C*P'+Omega.
mu=Pi+C*P'*solve(A,Q-P*Pi).
M=C-C*P'*solve(A,P*C); predictive covariance=Sigma+M.
This is Gaussian conditioning algebra equivalent to the cited inverse form.
It avoids explicit inverses. No views yields mu=Pi and M=C. Sigma (not M) is
the chosen optimization risk matrix, matching the cited worked example.

One absolute view P=[1,0], Q=.10, tau=.05 and Omega=.002 gives mu=(.08,.09),
M=diag(.001,.0045), predictive=diag(.041,.0945). One relative view [1,-1]
uses a difference of excess returns, without adding the safe rate again.

The project confidence convention omega=((1-c)/c)*tau*p*Sigma*p' derives from
requiring a single posterior view mean to equal (1-c)*p*Pi+c*q. c=.5 is the
scaled-variance baseline in source equation 8; c=0 is omitted and c=1 has zero
error variance. This is not the full numerical Idzorek calibration, and multiple
views interact. At tau-scaled Omega the posterior mean is invariant to tau.

Published acceptance fixture: Idzorek Table 5's eight-asset covariance and
Table 1 rounded priors, the three picks/opinions in the paper, tau=.025 and
equation 8 Omega reproduce Table 6 annual means within 0.0001 (one basis point).
Maximum discrepancy from rounded publication inputs/outputs is .0000635143.
The paper's unconstrained weights sum to 103.63%; we do not use those as
long-only fully-invested production targets. Fixture source and tolerance are
saved alongside the numbers; no published performance is attributed to our code.

### Constrained allocation and rebalance ledger (project derivations)

Minimize f(w)=delta/2*w'*Sigma*w-mu'*w subject to sum(w)=1 and 0<=w_i<=cap_i.
Projection has w_i=clip(v_i-theta,0,cap_i), with theta solved by bisection so
weights sum to one. Projected gradient step size is 1/(delta*lambda_max(Sigma)).
A certificate is gap=grad(f)'*(w-s), where s minimizes grad(f)'s over the capped
simplex (fill lowest-gradient assets first). Convexity bounds objective error
by this gap. Tolerance is in utility units. For a positive-definite Hessian,
weight error <=sqrt(2*gap/lambda_min(delta*Sigma)); it is not equal to gap.
No views recovers a feasible reference portfolio. With identical risk/return,
two assets receive .5/.5; a dominant asset and cap .6 produce .6/.4.

For delayed execution, V is NAV at observed execution marks, R_i current equity
values, F the current monetary floor, w_i the frozen sleeve mix, g the planned
whole-portfolio equity fraction and e the configured equity share of risky
capacity. For trial post-cost NAV x:
E_i(x)=w_i*min(g*x, e*min(m*max(x-F,0),cap*x)).
Solve x+k*sum_i|E_i(x)-R_i|=V; k is total commission/spread/slippage per reference
notional. Configuration enforces k*max(1,e*m)<1, making this equation strictly
monotone. Safe cash=V-costs-sum(E_i); each cost component is separately recorded.
Emergency sets E=0. Budget is rechecked after costs and adverse opening gaps.

Hand example: V=1000, all cash, F=800,m=3,e=.75,k=.03 gives total equity
E=2.25*(1000-.03*E-800)=450/1.0675. NAV+costs=1000 and E obeys the post-cost
budget. In a fully risky .5/.5 target, holdings600/400 plus200 contribution
become600/600 with no sale and zero costs. These are self-financing conventions,
not equations attributed to a Black-Litterman publication.

## Phase 5: systematic relative views (package 0.7.0)

Contract: [SYSTEMATIC_VIEWS.md](SYSTEMATIC_VIEWS.md). Financial values are
fractions, prices share one currency and adjusted-close basis, timestamps are
UTC. All inputs must be available at the relevant historical decision time.

### Price descriptors and normalization

Momentum M(t) = P(t-s)/P(t-L) - 1, with L=252 and s=21 sessions by default.
This is a project session-count proxy for prior 2-12 month momentum; it does
not reproduce French's size-sorted portfolio factor (`french_daily_momentum`).
Sample volatility = sqrt(A * sum((r_j-r_bar)^2)/(n-1)), r_j=P_j/P_(j-1)-1,
A=252, n=63 by default. Annualization assumes comparable daily observations;
square-root scaling is a convention, not evidence of independent market returns.

Across N assets: mean=sum(x_i)/N, sigma=sqrt(sum((x_i-mean)^2)/N),
z_i=clip(direction*(x_i-mean)/sigma, -cap, cap).
Constant cross sections return zero; missing data never becomes zero.
Composite S_i=sum(weight_k*z_ik), weights positive and sum to one.
Defaults momentum +1/.6 and volatility -1/.4, cap=3 are project choices.
MSCI (`msci_quality_2022`) supports normalization background only: population
scaling and clipping after standardization are our explicit convention.

Hand checks: prices 100,110,121,108.9 with L=3,s=1 give momentum .21.
Last two returns .10,-.10 have sample variance .02 (A=1).
Values 1,2,3 have mean 2 and population sigma sqrt(2/3), z=(-sqrt(1.5),0,sqrt(1.5)).

### Fitted mapping, units and uncertainty

Fixed preselected asset pair A,B: x=S_A-S_B. Labels are H-session simple
return differences y=(P_A,end/P_A,start-1)-(P_B,end/P_B,start-1).
Start must not precede the feature decision. Only completed, available labels
before the configured embargo can enter a fit; intervals cannot overlap.
Default H=21. Each sample preserves both raw price paths and feature provenance.

OLS (`nist_ols`): b1=sum((x-x_bar)*(y-y_bar))/Sxx,
Sxx=sum((x-x_bar)^2), b0=y_bar-b1*x_bar, yhat=b0+b1*x0,
s2=sum((y-b0-b1*x)^2)/(n-2).
Variance of the fitted conditional mean is
u=s2*(1/n+(x0-x_bar)^2/Sxx), under independent homoskedastic errors and
fixed predictors. This is not future-outcome variance (which adds s2);
see `nist_mean_response`. Assumptions remain unverified on market data.

Annual view Q=(A/H)*yhat; annual mean variance u_ann=(A/H)^2*u.
This arithmetic scaling does not claim compounded annual wealth.
P has +1 for A and -1 for B. Set omega0=max(u_ann, configured_SE_floor^2),
v=tau*P*Sigma*P', c=min(configured_cap,v/(v+omega0)),
Omega=v*(1-c)/c. This inverts the phase-4 single-view confidence convention;
it is not a success probability or full Idzorek numerical calibration.
Only one pair is fitted, avoiding an unsupported diagonal independence
assumption across several views sharing fitted coefficients.

Hand OLS example: x=(-1,0,1,2), y=(-1,1,2,4) gives b0=.7,b1=1.6,
s2=.1; at x0=.5, yhat=1.5 and u=.025. If v=.004 and c=.75,
Omega=.004/3. A and B period returns .05 and .02 imply label .03.
Tests in tests/test_factors.py verify these equations, temporal selection,
revisions, non-overlap, confidence constraints and replay from raw inputs.

Insufficient/stale labels, constant scores, extrapolation or forecast magnitude
outside configured bounds yield NO_VIEW and the phase-4 no-view prior.
Malformed or tampered evidence raises an error instead of an allocation.
Synthetic walk-forward comparisons are engineering evidence only; no model
promotion or verified market profitability follows from these tests.

## Phase 6: fixed-rule EUR/USD research baselines (0.8.0)

Contract: FX_BASELINE.md. Sources and qualifications are in the phase-6
bibliography records. Price S is USD/EUR; q is signed EUR units; account P&L
is USD. This is a collateralized linear exposure experiment, not a spot broker
settlement model or a prediction of economic profitability.

### Descriptors and rules

SMA_n(t)=sum(last n completed 4H closes)/n (`fidelity_sma`).
Trend=SMA_fast/SMA_slow-1. Direction=+1 above configured +threshold, -1 below
-threshold, else zero. Fractional momentum=S_last/S_first_in_slow_window-1
(`fidelity_roc` reports percentage ROC; this project omits the factor 100).

For the mean-reversion descriptor: m=mean(last n prices),
s=sqrt(sum((S_i-m)^2)/n), z=(S_last-m)/s, or zero if s=0.
Direction=-1 if z>configured bound, +1 if z<-bound, else zero.
This population-price z-score and contrarian rule are project conventions;
`fidelity_bands` provides only SMA/std envelope background. They do not
establish stationarity or assert that an envelope touch predicts reversal.

Policy proxy d=r_EUR-r_USD in annual decimals. Direction=sign(d) outside a
symmetric configured threshold, else zero. FRED percent observations convert
by dividing by 100 (`fred_fed_upper`, `fred_ecb_deposit`). Fed target upper
bound and ECB deposit rate are not identical instruments; this asymmetric
proxy is explicitly named. Carry motivation and risks: `gagnon_chaboud_2007`.
It is not uncovered interest parity or a calibrated return forecast.
Missing/stale prices or required rates give NO_TRADE. All thresholds are
illustrative configuration. This phase supplies no stop-based sizing model.

Hand checks: closes (1,2,3,4), fast=2,slow=4 give SMA_fast=3.5,SMA_slow=2.5,
trend=.4, fractional momentum=3. Mean=2.5, population std=sqrt(1.25),
z=1.5/sqrt(1.25). EUR .04 minus USD .03 = .01 (100 basis points), a long
candidate when the threshold is .0025. Constant prices have z=0.

### Accounting and costs

Quote convention: `cme_fx_quote`. Price P&L=q*(S_new-S_old).
If q=+1000 EUR and S rises 1.00->1.01, P&L=+10 USD; q=-1000 gives -10.
For total per-side cost rate c=(commission_bps+half_spread_bps+slippage_bps)/10000
and configured exposure f: entry notional=V*f/(1+c*f), q=direction*notional/S.
Derivation: notional=f*(V-c*notional). Closing/reversing costs apply to actual
exit notional, then a new entry is sized using the remaining NAV.

Fill price=S*(1+sign(delta_q)*(half_spread_bps+slippage_bps)/10000).
Reference-price P&L minus explicit spread/slippage and commission counts costs
once. Hand case V=10000,f=.1,c=.01,S_entry=1,S_exit=1.01 gives entry notional
999.000999..., total costs 20.0799200799 and final long NAV 9989.9100899101.

For elapsed dt=seconds/(365*86400), safe=prior_NAV*r_safe*dt,
carry=abs(q)*prior_S*r_direction*dt. Signed net long and short annual carry
are independent configuration, not inferred from the policy-rate feature.
A flat 1000 USD notional held half an hour at annual carry -.365 loses
1000/48000=.0208333 USD; +.365 gains the same. Safe collateral at .365 over
ten half-hours compounds incrementally as 10000*(1+1/48000)^10.
These are declared ACT/365 research accrual conventions, not broker rollover
or Wednesday triple-swap replication.

Ledger identity: final NAV = initial + price P&L + safe income + carry - costs.
Closed trade P&L=gross price P&L + trade carry - entry/exit costs. Tests reconcile
this total with NAV change excluding collateral income, including short trades.

### Timing, metrics and evidence

Only complete 30m/1H/4H/D UTC buckets with available_at<=decision enter a signal.
Execution uses an observed open strictly after the signal, with expiry; final
liquidation is fixed before each test fold. No downloaded vintage is backdated.
Fixed rules are evaluated on three chronological holdouts with prior warm-up;
no estimated parameters or test-based selection is claimed.

Metrics follow explicit definitions in FX_BASELINE.md and metrics.py:
MDD=max(1-NAV/running_peak); profit factor=sum(wins)/abs(sum(losses));
expectancy=mean(net trade USD); hit rate=positive trades/all trades;
CAGR=(final/initial)^(365/elapsed_days)-1; Calmar=CAGR/MDD.
Daily Sharpe uses a zero-rate benchmark and sample std times sqrt(252);
Sortino uses zero MAR and sqrt(mean(min(r,0)^2)). Undefined ratios are null.
Turnover=sum(abs(filled EUR)*reference_price)/initial_NAV; exposure is held
seconds/elapsed seconds. Holding time is elapsed hours; tail diagnostic is
worst completed trade USD. These definitions are not empirical significance.
Hand equity path 10000->10100->9898 gives net return -.0102, MDD .02,
trade expectancy -51 and profit factor 100/202 for net trades +100,-202.

Synthetic validation establishes numerical behavior and causality only. Live
Yahoo capture tests the plumbing, not historical performance. The initial FRED live failure
was corrected in 0.8.1: 88 real rate observations and macro-proposal replay
verified acquisition. Missing data still gives NO_TRADE, and current capture
does not supply historical publication vintages.

## Phase 7: FX volatility, stops and risk sizing (0.9.0)

Contract: FX_RISK.md. Raw prices are USD/EUR; quantities are EUR; capital,
costs and P&L are USD. Data must satisfy available_at <= decision. These risk
models cannot select direction or override independent hard account limits.

### Volatility equations and estimator identity

r_t=ln(S_t/S_(t-1)) on completed observed 4H bars. Historical sample variance
s2=sum((r-r_bar)^2)/(n-1); sigma=sqrt(s2). Weekend gaps enter the next observed
return; this is not equal wall-clock sampling or high-frequency integrated RV.

EWMA: h_next=lambda*h+(1-lambda)*r^2, zero conditional mean (`riskmetrics_1996`,
section 5.2). Seed h=mean(r^2) over the first seed window; subsequent returns
update h exactly once. Finite seed and the 4H lambda are project choices.

GARCH(1,1): h_next=omega+alpha*r^2+beta*h, omega>0, alpha,beta>=0,
alpha+beta<1 (`bollerslev_1986`, equations 2/8, Theorem 1). Project variance
target v=mean(r^2), omega=(1-alpha-beta)*v follows the stationary variance
identity. A configured finite alpha/beta grid minimizes mean(log(h)+r^2/h)
over observations after the seed, predicting each observation before updating
h. This is restricted Gaussian quasi-likelihood (section 5, constant/factor
omitted), not continuous MLE. Parameter estimation uses only the current
known historical window. All grid candidates are audited; none chosen by OOS.

Hand cases: (.01,-.01,.01,-.01) gives sample variance .0004/3.
EWMA h=.0001,r=.02,lambda=.94 gives .000118. With seed (.01,-.01), then
(.02,-.02),lambda=.5 gives h=.000325. GARCH h=.0001,r=.02,omega=.000001,
alpha=.1,beta=.8 gives .000121. For the four-return targeting example
(.01,-.01,.02,-.02), v=.00025,omega=.000025 with alpha=.1,beta=.8;
the two updates yield .000145 and .000181. Gaussian score is
[log(.0001)+4+log(.000145)+.0004/.000145]/2.

### Stop/TP and cost-aware sizing (explicit project composition)

D=max(min_pips*.0001, S*k*sigma*sqrt(H)); reject D>=S*maximum_stop_fraction.
This is linearized/frozen-variance policy scaling, not a GARCH multi-period
forecast or confidence coverage. Default H=1. Stop=S-d*D; TP=S+d*R*D.
For S=1.2,k=2,sigma=.005,H=1, D=.012. With H=4, D=.024. At very low sigma
the configured 5-pip floor gives .0005, not a 5%-price rule.

Stop-first sizing source: `cme_position_sizing`. Let V=NAV, F=FX capital,
f=risk_per_trade, p=portfolio risk fraction, O=already open risk,
c=per-side cost rate, T=max holding hours/(365*24), and r_c be the direction's
signed net carry rate. B=min(F*f,max(0,V*p-O)). Define exit bound
E=S+max(1,R)*D and loss per EUR L=D+c*(S+E)+max(0,-r_c)*E*T.
Pre-rounding quantity is capped by:
- B/L;
- (V*p-O)/(L+S*c*p), floored at zero, enforcing q*L+O <= (V-q*S*c)*p;
- (absolute_notional_cap-open_notional)/S, floored at zero;
- (V*n-open_notional)/(S*(1+n*c)), floored at zero, for portfolio notional fraction n;
- free_FX_margin/(S*(1/leverage+c)), reserving entry costs as well as margin;
- maximum quantity.
Round the minimum cap DOWN to unit_step; reject below minimum size.
Independent kill switch and concurrent-position guard can reject any candidate.
Pip value=q*.0001 USD; stop pips=D/.0001; their product equals q*D USD.

Hand sizing: V=10000,F=1000,f=.01,D=.01,S=1, no costs/carry and loose other
caps gives q=1000 EUR, 100 pips, .10 USD/pip and 10 USD stop risk. Doubling D
halves q to 500. D=.011 and step 100 gives 900 EUR. With R=2,c=.001,
r_c=-.365 and 48 hours, per-EUR loss is .01+.001*(1+1.02)+1.02*.365*48/(365*24);
quantity is floor(10/L) with unit step 1. Tests verify post-cost portfolio/margin
bounds independently and show that no model forecast overrides them.

### Execution tests and limitations

At a long stop .99 from entry 1 with 1000 EUR, loss is 10 USD before costs;
the short counterpart at 1.01 is the same. A long TP 1.02 earns 20 USD before
costs. A gap from 1 to .97 loses 30 USD and can breach a 10 USD budget.
Stops fill adverse gaps at open; TP gets no gap improvement; both-touched
candles resolve stop first. Long/short accounting, reserve-bounded normal
stops, time exits, stale entries and exact replay have hand tests.

Actual trade loss includes entry/exit costs and accrued carry. The declared
risk bound excludes beyond-barrier gaps, closure-delayed exits, underestimated
costs and safe-asset losses. Gap breaches remain visible in acceptance reports.
For diagnostics after a forecast is frozen, next squared log return y=r^2 is
a noisy variance proxy: QLIKE=log(h)+y/h and variance error=(h-y)^2. These are
not future inputs, a profitability claim or an automatic promotion criterion.


## Phase 8 — causal FX regimes (2026-09-25)

Primary verification: Rabiner (1989), DOI 10.1109/5.18626,
[original paper, MIT-hosted copy](https://web.mit.edu/6.435/www/Rabiner89.pdf),
pp. 262–265 and 267, equations 18–21, 37–40, 49–54.
For one Gaussian per state:

- b_j(x) = exp(-(x-mu_j)^2/(2*v_j)) / sqrt(2*pi*v_j).
- alpha_1(j) = pi_j*b_j(x_1);
  alpha_t(j) = b_j(x_t)*sum_i(alpha_(t-1)(i)*A_ij).
- Filtered p_t(j) = alpha_t(j)/sum_k(alpha_t(k)).
- Training beta_T(j)=1; beta_t(i)=sum_j A_ij*b_j(x_(t+1))*beta_(t+1)(j).
- gamma_t(j) = normalized alpha_t(j)*beta_t(j).
- xi_t(i,j) = normalized alpha_t(i)*A_ij*b_j(x_(t+1))*beta_(t+1)(j).
- pi'_j=gamma_1(j); A'_ij=sum_(t<T)xi_t(i,j)/sum_(t<T)gamma_t(i).
- mu'_j=sum_t gamma_t(j)*x_t / sum_t gamma_t(j).
- v'_j=sum_t gamma_t(j)*(x_t-mu'_j)^2 / sum_t gamma_t(j).

Backward probabilities are used only in training. Holdout labels use forward
filtering with frozen parameters. Gaussianity and conditional independence
are model assumptions; EM convergence does not establish market validity.

### Project policies and units (not sourced trading rules)

Input r=ln(close_t/close_previous), per observed 4H trading bar. Training x=(r-c)/s
with c=training mean, s=population standard deviation. Physical means c+s*mu,
variances s^2*v. Holdout log density subtracts n*ln(s) for the scale Jacobian.
Training likelihood history is in standardized units.
Defaults: 60 training returns, 2 states, 200 iterations, relative tolerance 1e-5
against max(1,abs(previous likelihood)); fail UNKNOWN on nonconvergence.
Initialization: uniform pi, diagonal A=.9 with .1 split across other states,
means at evenly spaced empirical quantiles .15 to .85, variances 1.
Constrained variance floor 1e-4 in standardized squared units; zero-occupancy
states or material likelihood decreases are rejected. States sorted by fitted
variance then mean; no semantic stress/trend names attached. All matrix axes,
initial and last-filtered probabilities are permuted consistently.

The independent transparent rule uses E=sum(r)/sum(abs(r)), or zero for a
constant path, and sample sigma=sqrt(sum((r-mean)^2)/(n-1)). On 12 returns,
E>=.4 means up, E<=-.4 down, otherwise sideways; sigma<.001 low,
sigma>=.003 high, otherwise medium. These configurable thresholds are project
conventions. One-hot membership is not statistical confidence; sideways is not
proof of mean reversion. Events/stress remain unclassified without supporting
data. UNKNOWN=1 denotes abstention, never a learned state probability.

Net trade attribution: net=gross+carry-costs; group sums plus safe income equal
final NAV minus initial NAV. Expectancy=sum(net)/trade count; hit rate counts
strictly positive net trades; holding time is the arithmetic mean. Assign only
the known entry-decision state, not a later/ex-post classification.

### Hand-checkable and independent tests

Emissions [[.5,.25],[.25,.5]], pi=[.6,.4], A=[[.7,.3],[.2,.8]]:
first posterior [.75,.25]; next predictive [.575,.425]; next posterior
[23/57,34/57]; sequence likelihood .1425. N(0;0,4)=1/sqrt(8*pi).
A separate exhaustive enumeration of all eight three-observation state paths
checks likelihood, smoothed training weights and expected transition counts.
Returns [.01,-.01,.01,-.01] give efficiency 0 and sigma=sqrt(.0004/3).
Attribution: trades +8 and -4 plus safe income +2 give NAV change +6.
Other tests cover future suffix invariance, frozen training revisions,
nonconvergence, missing/stale/gapped data, state ordering, scaling, reversal
entry lineage, numerical underflow, integrity and exact replay.


## Phase 9 — econometric forecasters (2026-09-25)

Accessible primary implementation sources:
[statsmodels AutoReg](https://www.statsmodels.org/stable/generated/statsmodels.tsa.ar_model.AutoReg.html),
[statsmodels VAR](https://www.statsmodels.org/stable/vector_ar.html),
[Kalman implementation by its statsmodels author, Chad Fulton](https://www.chadfulton.com/topics/implementing_state_space.html),
[statsmodels MarkovRegression](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html).
Markov estimation also reuses the verified Rabiner Gaussian-HMM equations from
phase 8. No statsmodels dependency is introduced: the small restricted models
are implemented with existing NumPy. Attempts to retrieve Kalman's original
1960 PDF failed; no claim of direct verification of that original is made.

### Linear models and units

r_t=ln(S_t/S_(t-1)); x_t=change in the as-of EUR-minus-USD annual-decimal policy
rate differential. All predictors at t are known when forecasting r_(t+1).
AR: r_(t+1)=a+phi*r_t+epsilon_(t+1).
ARX / chosen ARIMAX(1,0,0): add beta*x_t. There is no MA or integration term.
VAR: y_(t+1)=c+A*y_t+u_(t+1), y_t=[r_t,x_t]'.
OLS B minimizes ||Y-XB||^2 via full-rank least squares; residual covariance
E'E/(n-k). One-step prediction is [1,current predictors]*B. VAR stability uses
the spectral radius of A; scalar AR uses abs(phi). Software may alternatively
report inverse polynomial roots, which have the opposite unit-circle inequality.

Policy: training-window population centering/scaling for numerical conditioning;
restore return means and variances to original units. AR/ARX use scalar residual
innovation variance, VAR its first diagonal entry; parameter uncertainty is not
included. Orders fixed at one, no data-driven lag search. Default spectral
radius limit .995 is a research margin, not the theoretical boundary 1.

### Time-varying coefficients / Kalman

Standardized r_t is z_t. State b_t=[intercept_t,phi_t]' follows b_t=b_(t-1)+eta_t;
observation z_t=[1,z_(t-1)]*b_t+epsilon_t. Q=qI and R are configured.
Prediction: b_minus=b_previous; P_minus=P_previous+Q.
Innovation v=z-H*b_minus; F=H*P_minus*H'+R; K=P_minus*H'/F.
Update b=b_minus+K*v. Covariance uses the algebraically equivalent Joseph form
P=(I-KH)*P_minus*(I-KH)'+K*R*K', symmetrized against roundoff.
Next return mean uses H_next=[1,z_t]; variance H_next*(P+Q)*H_next'+R.
Multiply variance by training scale squared and restore mean units.

Policies: zero initial coefficients, P0=I, q=.001, R=.25 in standardized units;
all variance settings configurable. Reset and filter the completed rolling
window; do not smooth future observations into previous decisions. Last phi
and covariance are screened, not silently clipped. This is a random-walk
coefficient AR model, not an automatically estimated optimal noise model.

### Markov switching

r_t=mu_(S_t)+epsilon_t, epsilon conditional on S_t is Gaussian with variance
v_(S_t). State transitions A_ij=P(S_(t+1)=j|S_t=i).
With filtered last-state p_t, next-state probability q=p_t*A.
Predictive mean m=sum_j q_j*mu_j; variance
sum_j q_j*[v_j+(mu_j-m)^2]. The between-state term must not be omitted.
Training uses the phase-8 Gaussian EM/filter, refit ONLY on the current window.
No AR lags are included; this is switching mean/variance, not Hamilton AR(4).

Policies: minimum fitted state share .02, two states, variance floor inherited
from phase-8 settings, convergence required. Fitted state shares use training
smoothing only. Predictions use filtered endpoint followed by a transition;
using the endpoint posterior directly for next-period means would be wrong.

### Baselines, signal convention and diagnostics

No-change forecasts zero log return; momentum forecasts the last log return.
Both retain sample return variance for descriptive consistency. Neither is a
fitted probabilistic classifier. For all models, trade direction requires
abs(mean) > 2*c + configured_buffer + max(0,-annual_carry_for_side)*H/(365*24),
where c sums one-way fee/spread/slippage rates and H is maximum holding hours.
This first-order hurdle is a PROJECT HEURISTIC in approximate return units,
not a theorem about expected net profitability. Actual ledger costs/carry and
phase-7 hard sizing limits still apply independently.

MAE=mean(abs(predicted-actual)); RMSE=sqrt(mean(error^2)); sign accuracy includes
zero as a distinct sign. Information coefficient is Pearson correlation only
when both samples have nonzero variance. Paired zero-return baseline MSE is
mean(actual^2) on the same labels; skill=1-MSE/model_baseline_MSE if denominator
is positive. No labels beyond holdout end enter scores. Completed-holdout
coverage/drawdown screens are diagnostic, not inputs to that holdout's trades.
VECM remains disabled until both empirical and economic prerequisites pass.

### Hand checks and acceptance tests

OLS X=[(1,-1),(1,0),(1,1)], Y=[1,0,3]': coefficients [4/3,1], residual variance
8/3, forecast at x=2 is 10/3. Exact recursions check AR coefficient .5,
ARX .001+.4*r+2*x, and VAR c+A*y with A=[[.5,.2],[-.1,.3]].
Scalar Kalman b0=0,P0=1,H=1,Q=0,R=1,z=2 gives b=1,P=.5,F=2.
With Q=1: b=4/3,P=2/3,F=3. Vector H=[1,1],P0=I,z=3,R=1,Q=0
 gives b=[1,1], P=[[2/3,-1/3],[-1/3,2/3]].
Mixture q=[.25,.75], means [0,.02], variances [.0001,.0004] gives
mean .015, total variance .0004. Forecast errors [.01,.01] give MAE=RMSE=.01.
Cost example: three one-way charges of 1bp plus 1bp buffer gives 7bp hurdle
before carry. Independent tests cover causality, revisions, missing macro,
explosive roots, degeneracy, nonconvergence, kill switch, ledger source parity,
no-trade accounting, scoring boundaries and exact bundle replay.
