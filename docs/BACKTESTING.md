# Phase 3: execution contract

This is an engineering backtesting core, not evidence of profitable historical
trading. The phase-1 daily harness and its accepted model equations are unchanged.
`portfolio_backtest` supplies an independent next-open execution convention.
Configuration: `config/backtest.json`. Baselines: static, CPPI, TIPP, using the
verified phase-1 exposure function. Dynamic models remain in the phase-1 lab;
this phase does not calibrate a new strategy or implement Black-Litterman/FX.

## Units and scope

One risky instrument plus a safe cash sleeve, all in one account currency.
Fractional units, long-only, no leverage, no shorts, no volume or partial-fill
simulation. The default risky budget invests 75% in the risky instrument; the
remaining FX capacity stays safe. Static invests 30%, leaving 70% safe while
FX is unused. These are configurable reference choices.

Bars are coherent positive unadjusted OHLC with explicit timezone-aware open,
close and availability timestamps, normalized to UTC. Monthly boundaries
use that normalized UTC calendar. Corporate actions must be resolved upstream
without mixing adjusted closes with unadjusted open/high/low. Current phase-2
clean data contain selected prices, not a certified execution-bar feed. There
is deliberately no implicit conversion of those closes to fictitious OHLC.

Strict mode requires complete bars available at their historical close. A late
release or today's downloaded historical snapshot is rejected. Policies receive
only the completed prefix, never the next open or future candle high/low. A
custom callable must not access external future data; externally supplied
vectorized targets likewise require their own causal provenance.

## Event order

1. Credit safe return and debit signed carry on prior-close holdings for the
   interval **previous close to current open**. Negative carry is a credit.
   First-bar rates apply to the initial account, so fixtures use zero initially.
   Intraday safe return/carry is explicitly zero in this daily core. Do not
   supply a full close-to-close yield as an overnight rate. Synthetic fixtures
   convert an effective annual 3% at ACT/365 over actual overnight intervals;
   this is scenario input, not an estimate of future yield. For a safe instrument
   with material intraday price risk, a future multi-asset engine is needed.
2. Resting bracket gaps execute at the opening reference price and cancel any
   pending rebalance. Otherwise yesterday's target order executes at today's
   open, with its spread/slippage and commission. The order cannot see the
   current candle's high/low/close. A target is a weight, not a fixed share order.
3. Evaluate resting stop/TP, including for a newly opened position. If both are
   reachable in a candle, assume stop first. This is an explicit conservative
   simulation convention, not a claim about the unseen price path.
4. Mark at close, compute return before external cash, then apply a contribution
   on the first observed close of each new calendar month (not at inception).
   Update contribution-adjusted HWM. Calculate the monthly target after cash.
5. Daily CPPI/TIPP monitoring may schedule emergency liquidation for the next
   open. There is no guaranteed continuous exposure cap or protection against
   overnight jumps. Time stop counts the entry bar as one completed bar and
   schedules liquidation next open. No same-bar reentry after a bracket exit.
6. The final pending order is reported but not force-filled or liquidated.

Safe returns/carry are realized accounting events, not signals. Unfunded carry
aborts the simulation instead of implicitly borrowing. Policies that raise or
return invalid decisions abort without publishing a completed result.

## Orders and prices

Commission, half-spread and adverse slippage are separate bps settings, each
charged on absolute **reference** notional. This is an explicit proportional
cost model, not a broker fee schedule or observed historical spread.
Execution price = reference * (1 + side*(half_spread+slippage)/10000).
Commission remains a separate cash debit; spread/slippage are not charged twice.

A stop is a market exit; a gap below its threshold fills at the open, not the
old stop. A take-profit is a sell limit, checked against the price after adverse
impact. At a non-gap TP, the required reference touch is limit/(1-impact), so
net unit execution price never falls below the limit (commission excluded).
Other limit targets are explicitly **next-open-only**: if the opening effective
price violates the limit, the order expires. No inference of intraday limit
fills, queues, liquidity, stop-limit or partial-fill execution is made.

Anchors use reference entry prices, excluding fees. Additional purchases reset
the anchor and holding age; partial reductions preserve them. These conventions
are tested and visible in the trade ledger (open versus intrabar phases).

SEC primary source: [Types of Orders](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders)
and [Stop Order](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order),
accessed 2026-09-24. They support the distinction between market price uncertainty,
limit price constraints and stops becoming market orders. They do not establish
our OHLC fill, age, monthly calendar, cost or liquidity conventions.

## Research and reports

`research.daily_targets` independently computes daily rebalancing with vectorized
NumPy arrays, shifted close targets, overnight gaps, intraday returns, safe
income and proportional costs. Contributions, brackets, carry and time exits
are rejected there: final validation uses the event engine. Hand and mixed-price
tests reconcile every NAV and cost to that engine under matching assumptions.

Reports include terminal NAV, external contributions, flow-neutral TWR,
close-based maximum drawdown, costs, carry, safe income, fills, floor-breach
closes and pending terminal orders. No Sharpe optimization or strategy selection
is conducted on these synthetic fixtures. Full insurance research metrics
remain available in the phase-1 laboratory. Walk-forward model evaluation waits
for a suitable point-in-time dataset and an actual estimated strategy.

Each saved JSON contains inputs, execution and policy configuration, runtime
versions, source hash, all daily events, all fills, pending order and summary.
Checksum and exact replay detect tampering and changes in code or runtime. Replay
executes only installed code, never code embedded in an input artifact.

```powershell
.\.venv\Scripts\python.exe -m portfolio_backtest.cli --output reports/runs/phase3-my-run
.\.venv\Scripts\python.exe -m portfolio_backtest.cli --replay reports/runs/phase3-my-run/baseline--overnight_gap--cppi.json
```

The output directory must be new. Failed runs do not emit a success marker.
