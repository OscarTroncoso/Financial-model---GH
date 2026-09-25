# Phase 7 acceptance — 2026-09-25

**Locally PASSED, package 0.9.0**, under [FX_RISK.md](FX_RISK.md).
Phase 8 has not started. No brokerage routing is enabled.

| Requirement | Implementation and verification |
|---|---|
| Realized volatility | Rolling sample log-return variance, explicit ddof=1, hand case |
| EWMA | Sourced zero-mean recurrence and declared seed; hand recursion and chronological input tests |
| GARCH(1,1) | Sourced stationary recursion, variance targeting and audited finite-grid Gaussian fit; hand parameters/score and candidate constraints |
| Stop interface | Configured volatility distance, pip floor and rejection guard; no fixed 5%-price stop |
| Position sizing | Risk amount / total modeled loss per EUR, rounded down; long/short, pips, costs and carry hand checks |
| Independent risk limits | Per-trade/portfolio risk, post-cost notional, margin/leverage, min/max/increment quantity, concurrency and kill switch |
| Take-profit | Configurable gross reward multiple, actual-entry anchoring, conservative gap fill |
| Time stop | Precommitted 30m-aligned holding deadline, later available execution for closures/gaps |
| Stop-loss risk gate | Normal stops including modeled costs/carry stay within budget; independent post-cost cap tests |
| Gap honesty | Adverse 3% price-gap stress explicitly records a budget violation rather than guaranteeing the stop |
| Causality and audit | Completed as-of windows, future-suffix invariance, saved raw input/config/model and exact replay |

**269 tests pass, including 25 new phase-7 tests.** Three chronological holdouts
compare realized/EWMA/GARCH with a common trend rule, additional directional
and NO_TRADE controls, and elevated costs. Together with gap stress there are
**22 cases and 22 exact replays**. There are zero actual risk-budget breaches
in ordinary holdouts and one in the intentionally adverse gap stress.

Installed sources match all 63 workspace Python files. Dependency check,
installed GARCH-case replay and the corrected phase-6 replay pass. A risk plan
using the real Yahoo/FRED capture also saves/replays with a READY research
state and complete stop/TP/size; it remains non-executable for brokerage.
The illustrative account supplied for this check is USD 10,000 NAV and USD
1,000 FX capacity, not the user's actual account.

Evidence: [validation](../reports/phase7-validation.json),
[comparison](../reports/phase7-comparison.md), [metrics](../reports/phase7-metrics.json).
Full bundles and source snapshot are local under
reports/runs/phase7-accepted-20260925/ (Git-ignored). The suite ran against the
same sources before installation; byte equality and installed replay verify
that package 0.9.0 contains the accepted implementation. Remote CI not run.

## FRED prerequisite closed

Before phase 7, the public CSV transport was repaired and verified on 44 Fed
and 44 ECB observations with no source errors, plus raw-to-normalized and macro
proposal replay. FRED works for these current snapshots without API credentials.
See reports/fred-fix-validation.json. This supersedes the earlier phase-6
statement that live rate acquisition had not been verified. No historical
publication vintage or future service uptime is implied.

## Material limits

The GARCH fit is a constrained finite-grid, variance-targeted challenger, not a
full MLE or a demonstrated superior forecast. All stop/TP/cost parameters remain
research assumptions. A stop's modeled loss bound excludes adverse gaps,
closure-delayed exits and costs/carry worse than configured. Those scenarios
remain losses, not automatically repaired fills.

Financial performance evidence is synthetic. Real capture validates plumbing
and current as-of calculation, not historical predictive profitability. Account
currency is USD for this standalone linear FX ledger; EUR portfolio integration,
regimes, shadow/paper acceptance and broker execution remain later phases.
All equations, units, sources and project conventions are in MODELS.md and
FX_RISK.md. No financial model is promoted to live capital by these tests.
