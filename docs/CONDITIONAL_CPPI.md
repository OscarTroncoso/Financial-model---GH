# Conditional CPPI: equation review and implementation contract

Status: executable research challenger `conditional_cppi`, version 0.2.0.
It is an additional phase-1 comparison, not an alias for `volatility_adaptive`
or `adaptive`. The mandatory-model acceptance gate remains open.

## Published bound

Ben Ameur and Prigent, *Portfolio Insurance: determination of a dynamic CPPI
multiple as function of state variables*, December 2006 preliminary version,
section 3.2, positive-cushion case (PDF pp. 10-11, propositions/corollary p. 15).
[Original working paper](https://www.cranberger.com/sites/default/files/libs/Portfolio%20insurance.pdf).
The text extraction damages inequality signs, so the direction is also checked
algebraically below. This does not replicate their GARCH empirical experiment.

For positive discounted cushion C, constant discounted floor and no costs,
`C_next = C * (1 + m * R)`. If q<0 is a lower log-return quantile, nonnegative
cushion at that threshold requires `m <= 1/(1-exp(q))`. A nonnegative q gives
no finite upper bound from this condition. Equality permits zero cushion.

## Explicit laboratory estimator and policies

The published bound accepts a return distribution; these are our documented
baseline choices, not a claim that the paper prescribes these defaults:

- Relative asset return `x=(1+risky)/(1+safe)-1`, from completed observations.
  This expresses the risky asset in units of the defensive asset. A zero or
  negative defensive gross return aborts this model's run.
- Daily log returns `log(1+x)`. Rolling sample standard deviation with divisor
  n-1; window and minimum observations use the existing volatility configuration.
- Conditional Gaussian log-return mean fixed at zero. Horizon standard deviation
  `s_h=s_daily*sqrt(h)`, assuming independent, identically distributed increments
  with constant variance over the selected horizon. It is not a GARCH estimate.
- Lower log quantile `q=NormalInverseCDF(p)*s_h`. Defaults p=0.01 and h=21 market
  observations are illustrative. They are not a fitted probability or an exact
  monthly calendar, and do not cover the extra execution delay automatically.
- Choose the largest multiplier satisfying the published bound and configured
  maximum. If that is below the configured minimum, use zero, not the minimum.
  No base-multiplier, target-volatility, elasticity or regime factor is used.
- Warm-up stays safe; becoming ready does not trigger an unscheduled purchase.
  A -100% risky relative return permanently prevents re-entry on that input path.
- `floor_policy` selects capital, TIPP or drawdown; comparison default is TIPP.
  The published bound is therefore only a local risk-sizing diagnostic: the
  lab's ratcheting/nominal floor, costs and delays violate its idealized setup.
- Old pending buys are cancelled when they exceed the newly observed pre-cost
  risk budget, even if optional emergencies are disabled. Fees may subsequently
  reduce cushion; the simulator records that instead of claiming a guarantee.
- An unusable estimate queues a delayed full exit independently of optional
  emergency rules. Existing hard caps and emergency logic remain independent.

**No 99% protection promise:** p concerns a chosen endpoint distribution, not
pathwise floor protection. Parameter uncertainty, fat tails, changing volatility,
negative defensive returns, floor movements and execution costs matter. These
synthetic runs test mechanics, not probability calibration or expected utility.

## Hand calculations and tests

| Input / property | Expected | Test |
|---|---|---|
| q=log(0.8), cap=10 | m=5; 20 cushion minus 100 exposure times 20%=0 | test_twenty_percent_loss_implies_multiplier_five |
| q=log(0.5), cap=10 | m=2 | test_half_loss_implies_multiplier_two |
| bound=2, minimum=3 | zero, never override bound | test_minimum_never_overrides_risk_bound |
| daily logs +0.1,-0.1; h=2 | horizon std=0.2 | test_estimated_log_std_and_horizon_by_hand |
| p=Phi(-1), horizon std=0.2 | q=-0.2 | test_gaussian_quantile_one_standard_deviation |
| equal risky/safe returns | zero relative volatility | test_relative_returns_use_defensive_numeraire |
| future returns modified | earlier estimates/decisions identical | test_future_data_cannot_change_estimates_or_decisions |
| adverse data arrives before queued buy | cancel buy | test_stale_pending_buy_cannot_exceed_new_quantile_budget |

Each audit event stores the multiplier, estimator status, observation count,
horizon, horizon log volatility, log quantile and source/version identifier.
Existing `volatility` remains the annualized simple-return volatility used for
monitoring; it must not be confused with the horizon log volatility in the
multiplier estimate. Run bundles contain every input and can be replayed.
