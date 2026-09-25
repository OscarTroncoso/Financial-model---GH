# Phase 8 acceptance â€” 2026-09-25

**Locally PASSED, package 0.10.0**, under [FX_REGIMES.md](FX_REGIMES.md).
Phase 9 has not started. Research only; no brokerage execution or regime-based
routing has been enabled.

| Requirement | Implementation and evidence |
|---|---|
| Transparent baseline | Configurable direction/path-efficiency and sample-volatility labels; one-hot membership explicitly distinguished from statistical confidence |
| HMM challenger | Gaussian emissions, training-only Baum-Welch, frozen scaling/parameters, log-domain forward filtering; original Rabiner equations verified |
| Point-in-time inference | As-of candle vintages; cutoff strictly before decisions; immutable training vintage; future-suffix and late-revision tests |
| Stored probabilities | Per-decision probability vectors, version, input lineage, training parameters, convergence trace and raw requests |
| Regime performance | Actual entry signal lineage, including reversals; net costs/carry, counts, expectancy, hit rate and holding time by state |
| Reconciliation | Grouped trade P&L plus separate safe income equals ledger NAV change |
| Safe failure | UNKNOWN on stale/missing/gapped data, degeneracy or failed convergence; malformed inputs rejected |
| Audit and reproducibility | Saved raw inputs/config/source identity and exact replay; archived source snapshot |

**292 unit/integration tests pass, including 23 phase-8 tests.** HMM checks
include a hand-computed two-state filter and an independent enumeration of all
eight three-observation paths. Tests also cover frozen training revisions,
forward-only holdout labels, numerical underflow, state ordering, scale
invariance and reversal attribution. An installed three-state smoke test passes.

**Three chronological holdouts, 15 cases, 15 exact replays.** Each fold compares
NO_TRADE, trend, mean-reversion and rate-differential rules, plus elevated costs
for trend. Both regime methods are evaluated on the unchanged phase-7 ledger.
There are 360 saved decisions per method across cases (repeated across strategy
comparisons, not 360 independent observations). All accepted cases have READY
rule/HMM records; separate unit tests verify UNKNOWN cases.

A Monday fold initially used Monday midnight as training cutoff and correctly
abstained. The final suite uses the last completed pre-weekend close. This is
covered by a regression test; the earlier review is retained separately and is
not accepted evidence.

Version 0.10.0 is installed, pip check passes and all 72 installed Python files
match workspace sources. The installed inference CLI saves and exactly replays
its example; an installed full evaluation replay also passes. An existing
phase-7 GARCH bundle still reproduces, verifying
preservation of the prior risk implementation. Remote CI was not run.

Evidence: [validation](../reports/phase8-validation.json),
[comparison](../reports/phase8-comparison.md), [metrics](../reports/phase8-metrics.json).
Full bundles and source snapshot: reports/runs/phase8-accepted-20260925/.
Tests: reports/runs/phase8-tests-final-20260925.log (292 tests, 64.933 seconds).
Source identity: `fdb582c22a5d82bab139a8db5023ecb472cbcad194d53e057a307f5dc346e139`.

## Limits and deferred scope

Evidence is synthetic engineering validation, not demonstrated predictive
value or profitability. The HMM is a locally fitted Gaussian challenger; its
variance ranks are relative to each training fold. Rules are documented project
conventions. Neither method proves mean reversion or identifies economic events
or crisis states. Costs/carry remain those of the phase-7 research contract.

No parameter tuning on holdout outcomes, random time split, future-smoothed
trading labels, live orders or risk overrides were added. Optional clustering
remains deferred; phase 9 econometric models require a separate task. FRED's
previous repair remains intact; a current vendor download does not supply
historical ingestion/release vintages.
