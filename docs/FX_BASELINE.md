# EUR/USD baseline contract â€” phase 6, package 0.8.0

## Scope

`portfolio_fx` implements free-data capture, causal OHLC/rate inputs, complete
30m/1H/4H/D alignment, three fixed-rule baselines, NO_TRADE, an initial proposal
object and a delayed signed-exposure research ledger. It is separate from the
phase-3 daily long-only equity engine because shorts and intraday clocks need
a different accounting contract. No earlier financial implementation changes.

Signals are research candidates, not executable orders. Stop, take-profit,
position size, expected risk and probability remain null, with
`executable=false` and `risk_status=phase7_risk_sizing_required`. The fixed
exposure used for comparison is explicitly not stop-based risk sizing.
The phase-7 volatility/risk engine and later broker gates remain unimplemented.

## Data and clocks

All prices are USD per EUR. Yahoo EURUSD=X provides indicative OHLC, not
certified executable bid/ask or centralized traded volume. Capture stores the
library output and a checksum-protected normalized JSON snapshot in a new
local directory. Raw all-missing quote rows remain null and are excluded from
normalized candles; partial invalid OHLC fails validation. No price filling.
The versioned phase-2 daily Datum store remains unchanged: FX snapshots retain
the OHLC and intraday clocks that its scalar daily contract does not represent.

For each completed 30m candle: start < end <= ingestion <= availability.
Timezone-aware instants normalize to UTC. Revisions are selected only after
filtering availability <= decision. Equal-time conflicts fail; exact duplicates
collapse in as-of selection. Current downloads retain actual ingestion and
cannot be used as if observed at historical closes.

Aggregation uses fixed UTC boundaries: 00:00/04:00/... for 4H, midnight for D.
A bucket requires every expected contiguous 30m candle. Weekend/partial sessions
are not manufactured. Daily bars are not New York-close broker bars. Each
aggregate retains all input starts and maximum availability. Signals use the
latest completed bucket and freshness checks for all four frames. Price-return
context across the last two buckets is audited but does not filter these simple
rules. The 4H window drives the rules; long historical gaps fail to NO_TRADE.

The FRED adapter accepts DFEDTARU (Fed target upper bound) and ECBDFR (ECB deposit
rate), percent divided by 100. Their difference is explicitly an asymmetric
**policy-rate proxy**, not matched-maturity bond yields or broker financing.
Release vintages are unknown: a conservative next-midnight observation and
actual ingestion determine availability. A failed series remains absent with
its error recorded. Rate rules require both known, fresh observations. Other
rules do not require rates. No macro values are fabricated or forward-released.

## Baseline identities

All defaults live in config/fx.json and are illustrative, not optimized.

- `no_trade`: flat FX exposure, with collateral/safe income.
- `trend`: 4H fast SMA / slow SMA - 1; long above +threshold, short below
  -threshold, neutral otherwise. Default windows 6/24, threshold .0005.
- `mean_reversion`: current 4H close's population z-score in a trailing
  20-close window; short above +1.5, long below -1.5, neutral otherwise.
  Constant prices give z=0. This is a contrarian research hypothesis, not proof
  of stationarity or a forecast that prices must revert.
- `rate_differential`: EUR policy proxy - USD policy proxy; long EUR above
  +.0025, short below -.0025. Carry-inspired directional hypothesis, not UIP,
  not a prediction of certain appreciation. Swap accrual is separate.

See MODELS.md for equations, hand checks and primary sources. Boundaries are
strict: equality produces neutral. There are no fitted probabilities or ML.
Insufficient/stale input yields NO_TRADE; malformed data raises an error and
no new allocation is produced. In the research ledger NO_TRADE means a flat
target at the next permitted execution, including closing an existing position.

## Research execution and accounting

Account currency is USD solely to evaluate linear EUR/USD exposure. This is
not conversion or integration into the user's EUR portfolio. Signed EUR units
q generate USD P&L q*(S_new-S_old). It is a fully collateralized linear exposure
simulation, not physical spot settlement, a broker-specific CFD or a futures
contract with expiry/basis. Collateral NAV earns configured safe income; net
long/short carry assumptions apply to absolute USD notional separately.

Decisions occur on the completed 4H clock; 30m bars provide execution marks.
An order fills at the first observed open strictly after the decision. Thus a
contiguous candle opening exactly at the decision is skipped, imposing a
conservative 30m delay. Excessively old pending signals expire to flat.
Changes of direction close first, then open; unchanged direction holds units.
Each holdout starts flat and precommits to liquidation at its last close.
Terminal pending signals are reported and never filled outside the holdout.

Default test exposure is 10% of post-cost NAV, capped by config at 100% on
entry. If marked notional exceeds collateral at a later observed open, the
ledger closes; gaps can still cause loss and insolvency aborts the run.
This guard is not a substitute for phase-7 stop/risk sizing or CPPI integration.

For an entry, notional = NAV*f/(1+f*c), where c is the per-side total cost rate;
q = direction*notional/S. Costs apply separately to entry and exit reference
notional: commission, half-spread and adverse slippage. Execution prices include
spread/slippage, and reference-price P&L subtracts those costs once, not twice.
Defaults .5 bps each are illustrative scenarios, not verified broker quotes.
The high-cost test uses 5 bps each. Quotes with no bid/ask require those assumptions.

For each elapsed interval dt in ACT/365 years: safe income = prior NAV*r_safe*dt;
carry = abs(q)*prior S*r_long_or_short*dt. Defaults are annual simple rates;
they are applied incrementally to marked balances. No Wednesday triple-swap
calendar is claimed. Continuous accrual over actual weekend time is explicit.
There are no contributions in these isolated FX holdouts. The full account
identity is initial NAV + price P&L + safe income + carry - all costs.
Completed trades reconcile to NAV change excluding collateral income.

## Validation and metrics

Three non-overlapping chronological holdouts use earlier history as warm-up.
The fixed rules have no fitted parameters; there is no random split or tuning
on held-out data. Synthetic fixtures exercise each baseline, flat benchmark,
long/short transitions and a higher-cost trend case: 15 cases with exact replay.
Full raw input, model settings, source hash, runtime, proposals and fills are
saved in each bundle. Future prices/rate releases cannot change an earlier
signal or the evaluated prefix. Hand tests cover accounting and timing.

Metrics include net return, drawdown, zero-rate Sharpe, zero-MAR Sortino,
ACT/365 CAGR/Calmar, profit factor, expectancy, hit rate, average win/loss,
win/loss ratio, exposure time, initial-NAV-normalized turnover, holding time,
worst-trade loss, costs and slippage. Undefined ratios are null. Daily ratios
use observed UTC daily equity closes and 252 sessions/year; partial first/last
days and tiny synthetic samples make annualized figures descriptive only.
No strategy is promoted based on synthetic performance. Real-vintage historical
OOS performance, empirical broker costs and EUR portfolio integration remain
separate acceptance work.

## Commands

Install the project after source changes. Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m portfolio_fx.cli --suite reports/runs/new-fx-suite
.\.venv\Scripts\python.exe -m portfolio_fx.cli --replay reports/runs/new-fx-suite/fold-1--trend--base.json
.\.venv\Scripts\python.exe -m portfolio_fx.cli --capture data/raw/new-fx-capture --days 30
.\.venv\Scripts\python.exe -m portfolio_fx.cli --signal-capture data/raw/new-fx-capture/normalized.json --model trend --output reports/runs/new-fx-signal.json
```

Use a new capture/suite/output path; existing artifacts are not overwritten.
`--at` optionally fixes an as-of signal timestamp. `--config` controls captured
signal model settings (default config/fx.json). Backtest `--input request.json
--output result.json` consumes explicit candles, rates, model, start, end,
config and execution fields; saved suite `payload.request` is a complete
example. The suite itself uses fixed declared fixtures, never silently reads
production config. `--replay` verifies experiment bundles and individual signal proposals, including
NO_TRADE, from saved market/rate inputs, decision/model/config.

Free intraday history is provider-limited, not a replacement for a long audited
vintage archive. A current capture can create an as-of research proposal but is
explicitly rejected as close-time historical backtest input.
