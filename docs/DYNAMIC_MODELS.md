# Phase-1 dynamic models: exact identities (0.3.0)

These are research baselines on a single aggregate risky return stream. Source
verification establishes an equation, not forecasting skill or a protection
promise. Every implementation convention below is distinct from a publication.

## volatility_adaptive: normalized inverse volatility

Use annual sample volatility of completed simple risky returns:

`m_raw = m0 * sigma_target / max(sigma_t, epsilon)`
`m = clip(m_raw, m_min, m_max)`

The inverse-volatility dependence is documented in Dangl, Randl and Zechner
(2015), section 3.2.5, as `m = 1/(z_a * sqrt(dt) * sigma_t)`:
https://link.springer.com/chapter/10.1007/978-3-319-09114-3_14
This is an accessible authored exposition, not access to Herold et al.'s original
2007 empirical implementation. Algebraically, setting the constant numerator
`1/(z_a*sqrt(dt)) = m0*sigma_target` yields our normalization. The zero-mean
Gaussian simple-loss constraint `m*z_a*sigma_h <= 1` independently yields that
inverse relationship. The conditional-quantile foundation is discussed by
Ben Ameur and Prigent (2006):
https://www.cranberger.com/sites/default/files/libs/Portfolio%20insurance.pdf

Normalization is a project risk policy: m0 is attained at sigma_target. The
configuration does NOT assert a particular tail confidence or horizon. It does
NOT target total portfolio volatility at sigma_target: volatility of the cushion
exposure depends on the cushion/NAV ratio. This differs from conditional_cppi's
lognormal-loss transformation. No calibrated probability is implied.

Baseline sigma is rolling sample std (n-1), annualized by sqrt(periods_per_year).
Only elasticity 1 is enabled. Other powers lack verification and are rejected.
Epsilon prevents zero division; it is a policy limit, not estimated risk.
Warm-up holds safe and waits for an ordinary monthly decision to enter.

Hand cases, m0=3, target=.15: sigma=.15 -> 3; sigma=.30 -> 1.5;
sigma=0 with epsilon=.001 -> raw 450 -> cap 5.

## adaptive: V4 composition with sourced drawdown response

Nystrup, Boyd, Lindstrom and Madsen, *Multi-period portfolio selection with
drawdown control*, Annals of Operations Research 282 (2019), eq. 6:
https://web.stanford.edu/~boyd/papers/pdf/multiperiod_portfolio_drawdown.pdf
https://doi.org/10.1007/s10479-018-2947-3
Their relative risk-aversion rule implies the reciprocal factor
`gamma0/gamma_t = (Dmax-D_t)/Dmax` below the drawdown limit.

Our explicitly named composition is:

`f_DD = max(0, 1-D_t/Dmax)` (zero when Dmax=0)
`m_raw = m0 * f_vol * f_DD * 1`
`m = clip(m_raw, m_min, m_max)`

Applying this factor to CPPI is a PROJECT COMPOSITION; it is not a published
canonical adaptive-CPPI model and does not reproduce the paper's multi-period
optimizer or its optimality results. TIPP's floor already reduces cushion in a
drawdown, so this extra factor intentionally reduces exposure again; the
comparison must determine later whether that conservatism is useful.

D_t uses the contribution-neutral, net-of-cost wealth index. A reached drawdown
limit forces m=0 even if m_min>0. This is an explicit hard policy. Re-entry needs
drawdown recovery AND the next monthly decision. There is no automatic reset of
loss history after a contribution. At D=.1, Dmax=.2 the factor is .5; with
volatility at its target and m0=3, m=1.5. Composition precedes clipping.

The phase-1 benchmark is V4, consistent with the V1-to-V5 research ladder.
The regime hook is present and neutral (`regime_factor=1`); other values are
rejected. A learned/estimated regime and V5 remain later research, not a falsely
implemented or invented phase-1 predictor.

## eppi: discrete Mancinelli-Oliva 2023 variant

Selected source: Mancinelli and Oliva (2023), section 2.3, equations 8 and 11:
https://doi.org/10.3390/risks11060105
Accessible article PDF:
https://pdfs.semanticscholar.org/93ef/d288ce43567f03d9289676712242d12b8627.pdf

For completed simple risky returns r_j:

`m_raw(t) = eta + sum(j=1..t, a*(1+r_j)**a*r_j)`; `eta>1`, `a>1`.

Equation 11 sets the empty sum to eta. This is additive and path dependent; a
price round trip need not restore eta. It is not the fixed-reference price-level
formula found in other accounts. The original Lee et al. 2008 equation pages
remain unavailable; we make no claim of reproducing that original version.

The application policy clips the OUTPUT multiplier, never its cumulative raw
state. It uses the shared configured floor and long-only budget `min(m*C,cap*V)`.
The risky stream is a synthetic reinvested-return proxy. There is no arbitrary
exponential function of cushion. eta and a are separate configurable parameters.
For eta=3,a=2: +10% adds .242; then -10% subtracts .162 -> raw 3.08.

The paper's printed wealth equation is not copied: with zero returns its safe
term would add principal again. Holdings accounting instead enforces the
self-financing identity `V_next = E*(1+r) + (V-E)*(1+safe_r)` before costs/flows.
This discrepancy limits any claim to replicating the paper's reported results;
the selected multiplier equation alone is reproduced.

## Shared execution and failure policy

All dynamic rules observe completed data and queue execution for the next
observation. Daily recalculation does not permit ordinary daily entry. A pending
buy is vetoed when the current risk budget has fallen below its intended size.
Costs can reduce cushion further; monthly/delayed trading cannot guarantee a
floor or continuously enforce a market-drifting exposure cap.

- A -100% risky return is an absorbing default for these new models, including
  after it leaves the volatility window. Subsequent returns cannot resurrect it.
- Nonfinite numerical calculations fail; no usable partial run is returned.
- Default/warm-up/drawdown-limit exits are queued even if optional emergency
  rules are off. Hard policy states override a positive minimum multiplier.
- Audit includes source ID, observations, raw multiplier and applicable
  volatility/drawdown/regime factors. Raw EPPI state is retained in every event.
- No leverage, shorts, FX trades or financing needs exist in this phase's proxy.

## Verification

`tests/test_dynamic.py`: arithmetic cases, limits, clipping order, raw EPPI
state, bad input, default, exhaustion, contribution neutrality, monthly timing,
execution delay, buy veto, reproducibility and future-prefix invariance.
Existing engine, accounting and conditional tests remain in force.
