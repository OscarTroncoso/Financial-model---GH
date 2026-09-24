# PROJECT_SPEC.md
# Adaptive Portfolio Insurance + Black-Litterman + EUR/USD Quant System

## 1. Product vision

Build a rigorous, modular portfolio-management system in Python that can evolve from research to shadow mode, paper trading, and eventually controlled live execution.

The system has three main economic "brains":

1. **Portfolio Protection Brain**
   - CPPI family / TIPP / adaptive multiplier / drawdown protection.
   - Decides how much of total wealth may be exposed to risk.

2. **Strategic Equity Brain**
   - Black-Litterman.
   - Allocates the equity sleeve across long-term stock holdings.
   - Stocks are primarily long-term spot holdings, not a high-turnover trading book.

3. **Tactical FX Brain**
   - EUR/USD swing-trading engine.
   - Uses market, macro, econometric, technical, volatility, regime, ML and later AI-derived structured features.
   - Produces `TRADE` or `NO TRADE`, plus entry, stop, take-profit and position size when a trade is valid.

All three are wrapped by:
- data engineering,
- risk management,
- backtesting,
- model registry/governance,
- audit trail,
- dashboard,
- scheduled automation,
- later IBKR paper/live integration.

---

## 2. Current strategic assumptions

These are provisional and must be configurable.

### 2.1 Reference allocation
Initial conceptual reference:
- Safe sleeve: ~60%
- Equity sleeve: ~30%
- EUR/USD risk capacity: ~10%

This **must not be implemented as a permanently fixed 60/30/10 portfolio**.

The intended hierarchy is:

1. Portfolio-insurance engine determines the permitted **risky budget**.
2. Within that risky budget, the provisional strategic split is:
   - 75% equities,
   - 25% FX capacity.
3. If the FX engine has no valid trade, unused FX capital remains in the safe sleeve.
4. Equity exposure is structurally more persistent than FX exposure.

Example:
- If permitted risky budget = 40% of NAV:
  - equity target reference = 30%,
  - FX capacity = 10%,
  - safe = 60%.
- If permitted risky budget falls to 24%:
  - equity reference = 18%,
  - FX capacity = 6%,
  - safe = 76%.

The 75/25 risky-sleeve split will later be researched and may be replaced by dynamic risk budgeting.

### 2.2 Contributions and rebalancing
- Capital contribution: monthly.
- Ordinary portfolio rebalance: monthly.
- Risk monitoring: daily or more frequently where technically justified.
- Emergency de-risking: allowed between monthly rebalances if hard limits are breached.
- New monthly capital should first be used to reduce portfolio drift before triggering unnecessary sales.

### 2.3 Safe asset
The current idea is to keep the defensive capital in a liquid low-risk fund yielding approximately 3% annualized at present.

Important:
- Do not model the safe sleeve as zero-return cash.
- Parameterize its realized/net return.
- Include fees, liquidity and any relevant risk.
- Do not treat a money-market/low-risk fund as legally guaranteed cash unless the actual instrument is guaranteed.

---

# PART A — PORTFOLIO INSURANCE ENGINE

## 3. Objective of the insurance layer

The insurance engine answers:

> How much total capital may be exposed to risky assets right now?

It is intentionally separate from the question:

> Which risky assets should we own?

Core quantities:

\[
V_t = \text{portfolio value}
\]

\[
F_t = \text{floor}
\]

\[
C_t = \max(V_t - F_t, 0)
\]

\[
E_t = \min(m_t C_t,\ E_{\max,t})
\]

Where:
- `V_t`: total portfolio value,
- `F_t`: protection floor,
- `C_t`: cushion,
- `m_t`: CPPI multiplier,
- `E_t`: allowed risky exposure,
- `E_max,t`: hard cap from risk policy.

The safe allocation is:

\[
Safe_t = V_t - E_t
\]

All formulas need explicit conventions for:
- timing,
- contributions,
- fees,
- safe return,
- negative/zero cushion,
- rounding,
- gap events,
- maximum risky exposure.

---

## 4. Research variants to implement

The project must **not immediately collapse all variants into one opaque model**.

Build and benchmark the following in parallel:

### 4.1 Traditional CPPI
Baseline:

\[
E_t = mC_t
\]

with fixed floor convention and fixed multiplier.

Purpose:
- reference benchmark,
- understand cash lock,
- establish expected behavior.

### 4.2 TIPP — Time-Invariant Portfolio Protection
Dynamic floor linked to the portfolio high-water mark:

\[
HWM_t = \max_{s \le t} V_s
\]

A typical formulation:

\[
F_t^{TIPP} = \alpha HWM_t
\]

where `alpha` is the protected fraction.

Purpose:
- lock in part of accumulated gains,
- prevent the floor from remaining tied only to initial capital.

### 4.3 Drawdown-based protection
A maximum drawdown-style floor can be expressed as:

\[
F_t^{DD} = (1-DD_{\max})HWM_t
\]

Note that TIPP and drawdown floors can become mathematically equivalent under certain parameterizations. Do not duplicate logic unnecessarily.

A generalized floor engine may use:

\[
F_t = \max(F_t^{capital}, F_t^{TIPP}, F_t^{DD})
\]

but only keep components that add distinct economic meaning.

### 4.4 Dynamic Multiplier CPPI
Multiplier responds to forecast risk instead of remaining constant.

Conceptual structure:

\[
m_t =
clip\left(
m_0 \cdot f_{vol,t},
m_{min},
m_{max}
\right)
\]

Possible smooth volatility adjustment:

\[
f_{vol,t}=
\left(
\frac{\sigma_{target}}{\hat{\sigma}_t}
\right)^{\gamma}
\]

Research sequence for volatility:
1. realized volatility baseline,
2. EWMA,
3. GARCH(1,1),
4. challengers such as EGARCH / GJR-GARCH / HAR when justified.

### 4.5 Adaptive CPPI
Extend multiplier adjustment:

\[
m_t =
clip\left(
m_0
\cdot f_{vol,t}
\cdot f_{DD,t}
\cdot f_{regime,t},
m_{min},
m_{max}
\right)
\]

Where:
- `f_vol` reacts to market risk,
- `f_DD` reduces exposure as portfolio drawdown worsens,
- `f_regime` reduces/increases exposure based on an independently estimated regime.

These factors should be smooth where possible; avoid unstable binary jumps unless a hard risk limit requires one.

### 4.6 Smart / algorithmic CPPI
Machine learning is **an overlay/modifier**, not an unrestricted portfolio controller.

Preferred role:
- estimate regime/stress probability,
- estimate risk state,
- modify permitted `m_t`,
- possibly veto additional risky exposure.

ML must not be able to override:
- floor constraints,
- leverage limits,
- drawdown limits,
- exposure caps,
- emergency de-risking rules.

Initial regime candidates:
- rule-based trend/volatility state,
- Gaussian Mixture / K-Means as research tools,
- Hidden Markov Model,
- Markov-switching models.

### 4.7 EPPI
EPPI is a separate challenger with its own variable-multiplier rule and state.
The earlier description as an exponential function of cushion was unsupported
and is corrected here explicitly. Phase 1 selects the discrete multiplier of
Mancinelli and Oliva (2023), equations 8/11, with tested self-financing accounting.
It does not claim to replicate the unavailable Lee et al. (2008) original.

Compare against CPPI, TIPP, volatility-adaptive and adaptive CPPI under the same
execution/cost assumptions. See `docs/DYNAMIC_MODELS.md` for exact identity.

---

## 5. CPPI/insurance research ladder

Implement progressively:

- V1: classical CPPI.
- V2: TIPP / dynamic floor.
- V3: TIPP + volatility-sensitive multiplier.
- V4: TIPP + volatility + drawdown multiplier.
- V5: TIPP + volatility + drawdown + regime.
- Challenger: EPPI.
- Later: ML-enhanced adaptive model only after simpler versions have been validated.

Do not skip directly to V5.

---

## 6. Monthly rebalance vs continuous protection

The user's ordinary rebalance preference is monthly.

Therefore separate:

### 6.1 Ordinary rebalance
Frequency:
- monthly,
- aligned with monthly contribution.

At this event:
1. ingest contribution,
2. update NAV,
3. update HWM,
4. update floor,
5. compute cushion,
6. compute dynamic multiplier,
7. determine risky budget,
8. determine equity and FX capacity,
9. use new cash to reduce allocation drift,
10. trade only amounts required after tolerance bands/cost constraints.

### 6.2 Risk monitoring
At least daily:
- NAV,
- HWM,
- floor,
- cushion,
- distance to floor,
- drawdown,
- realized/forecast volatility,
- multiplier,
- allowed risky budget,
- current risky exposure,
- exposure gap.

Monitoring does not automatically imply a rebalance.

### 6.3 Emergency de-risking
Research and specify hard conditions that can trigger action between monthly rebalances.

Candidates include:
- distance to floor below threshold,
- cushion utilization above threshold,
- realized/forecast volatility beyond critical level,
- drawdown near protection limit,
- gap-risk/event rule,
- actual risky exposure materially exceeds allowed risky exposure.

Emergency rules must:
- be explicit,
- be auditable,
- fail safe,
- be backtested with realistic execution delay and gap risk.

A monthly-rebalanced CPPI alone must **not** be described as guaranteeing the floor because markets can gap between rebalance points.

---

## 7. Insurance metrics

Do not select the insurance model solely by Sharpe.

Primary metrics:
1. number/magnitude of floor breaches,
2. maximum drawdown,
3. downside deviation,
4. capital-protection rate,
5. time spent near floor,
6. cash-lock frequency/duration,
7. upside capture,
8. CAGR,
9. Sortino,
10. Calmar,
11. realized volatility,
12. turnover,
13. costs,
14. average safe/risky allocation,
15. recovery participation after selloffs.

Stress tests:
- 2008-style equity crisis,
- 2020-style fast crash/rebound,
- prolonged bear market,
- volatility spike,
- overnight/gap shock,
- high-rate / low-rate safe asset,
- large contribution during drawdown,
- sequence-of-returns sensitivity.

---

# PART B — EQUITY SLEEVE / BLACK-LITTERMAN

## 8. Purpose

The equity sleeve is intended primarily for long-term spot holdings.

Black-Litterman answers:
> Given equilibrium returns, portfolio risk and systematic views, what should the target equity weights be?

It is **not** primarily a market-timing engine and should not be framed as finding the perfect sell point.

---

## 9. Black-Litterman pipeline

1. Define investable equity universe.
2. Obtain market-cap or chosen equilibrium weights.
3. Estimate robust covariance.
4. Infer equilibrium excess returns:

\[
\Pi = \delta \Sigma w_{mkt}
\]

5. Generate views `P`, `Q`.
6. Estimate view uncertainty/confidence `Omega`.
7. Compute posterior expected returns.
8. Optimize target equity weights under constraints.
9. Apply rebalance bands and transaction-cost logic.
10. Prefer monthly contributions to close underweights before selling.

Covariance estimators to compare:
- sample covariance,
- EWMA covariance,
- Ledoit-Wolf shrinkage,
- later dynamic covariance if evidence supports it.

---

## 10. Systematic Black-Litterman views

Views should be generated from structured evidence, not arbitrary opinions.

Potential feature groups:
- valuation,
- quality,
- momentum,
- growth,
- profitability,
- earnings revisions,
- balance-sheet metrics,
- volatility,
- macro sensitivity,
- analyst revisions,
- structured news/earnings-call signals.

The system must preserve:
- source feature values,
- mapping from features to view,
- confidence/uncertainty,
- timestamp,
- model/version that generated the view.

---

## 11. AI/LLM role for equities

LLMs may process:
- earnings calls,
- filings,
- investor presentations,
- company guidance,
- news.

Preferred output:
structured variables such as:
- earnings sentiment,
- guidance change,
- margin outlook,
- management confidence,
- regulatory risk,
- capex direction,
- demand commentary.

Required flow:

Text -> LLM extraction -> structured features -> quantitative view model -> BL view/confidence.

Avoid:
Text -> LLM -> direct unaudited BUY/SELL.

---

## 12. Equity exits

Initial version:
- Black-Litterman changes target weights.
- Rebalance bands prevent unnecessary turnover.

Later optional overlay:
- fundamental deterioration,
- material momentum breakdown,
- volatility shock,
- earnings deterioration,
- severe adverse news/regime.

This overlay must remain separate from BL so that strategic allocation and tactical risk reduction are identifiable.

---

# PART C — EUR/USD SWING TRADING ENGINE

## 13. Objective and style

Instrument:
- EUR/USD.

Style:
- swing trading, not high-frequency/intraday scalping.

Indicative data/timeframes:
- 30m for scheduled market update / trade check,
- 1H,
- 4H as an important primary swing timeframe,
- daily context.

The engine should not be forced to keep the FX sleeve invested.

Output:
- `NO_TRADE`, or
- direction,
- intended entry,
- stop,
- take-profit,
- position size,
- expected risk,
- confidence,
- reason/audit features.

The current 10% is best interpreted as **FX risk-capital capacity / maximum strategic reference**, not a permanent EUR/USD position.

---

## 14. EUR/USD data

Market:
- OHLC,
- bid/ask where available,
- spread,
- volume/market proxy if meaningful,
- calendar/session metadata.

Macro/rates examples:
- Fed policy expectations,
- ECB policy expectations,
- US 2Y,
- German/Euro-area 2Y,
- US 10Y,
- Bund 10Y,
- US-EU rate/yield differential,
- changes in the differential,
- inflation differential,
- growth data,
- PMIs,
- employment,
- NFP,
- CPI,
- PCE,
- central-bank decisions.

Risk/global context candidates:
- DXY,
- equity risk sentiment,
- volatility indices where useful,
- credit/risk proxies,
- commodities only if justified.

---

## 15. Macro surprise engine

For scheduled macro data, distinguish:
- consensus/expected,
- actual,
- prior/revised,
- release timestamp.

A standardized surprise can be researched:

\[
Surprise_t =
\frac{Actual_t - Expected_t}
{\sigma(Actual-Expected)}
\]

Do not leak revised data or future consensus into historical observations.

---

## 16. Fundamental AI engine for FX

Process:
- Fed statements,
- ECB statements,
- speeches,
- official releases,
- relevant macro news,
- geopolitical information where it plausibly affects the pair.

Structured outputs may include:
- Fed hawkish/dovish score,
- ECB hawkish/dovish score,
- relative monetary-policy score,
- inflation concern,
- growth concern,
- financial-stability concern,
- forward-guidance change,
- risk sentiment,
- confidence / source quality.

The NLP/LLM system must store:
- source timestamp,
- source identifier,
- prompt/schema version,
- extracted variables,
- confidence,
- model version.

No direct LLM-generated live trade without a quantitative/risk layer.

---

## 17. Technical features

Candidate research features:
- momentum,
- ROC,
- RSI,
- MACD,
- ADX,
- ATR,
- moving averages,
- moving-average distance,
- Bollinger width,
- realized volatility,
- breakout,
- trend strength,
- mean-reversion measures,
- support/resistance features,
- range/compression measures.

The goal is **not** to assume an indicator works universally.

Research:
- feature importance by regime,
- performance by timeframe,
- stability over time,
- incremental value after macro/risk features.

---

## 18. FX volatility engine

Purpose:
- quantify current/forecast risk,
- drive position sizing,
- help set stop distance,
- help set plausible target range,
- condition trade acceptance.

Research order:
1. realized volatility,
2. EWMA,
3. GARCH(1,1),
4. EGARCH,
5. GJR-GARCH,
6. HAR or other justified challengers.

Volatility models are primarily risk models, not directional predictors.

---

## 19. Regime detection

Desired states may include combinations of:
- trend / mean reverting,
- low / medium / high volatility,
- normal / event-driven / stress.

Progression:
- V1: transparent rule-based regime,
- V2: clustering/GMM for research,
- V3: HMM,
- V4: Markov-switching model.

Each inferred regime must have:
- timestamp,
- probabilities,
- version,
- inputs.

---

## 20. Model zoo

### 20.1 Econometric/statistical
Candidates:
- naive/no-change baselines,
- momentum baselines,
- AR/ARIMA,
- ARIMAX,
- VAR,
- VECM only when cointegration is established,
- Kalman filter / time-varying relationships,
- Markov-switching models.

### 20.2 Machine learning
Initial candidates:
- logistic regression,
- linear/elastic-net regression,
- random forest,
- XGBoost / LightGBM.

Potential targets:
- sign probability,
- expected forward return,
- probability of upper/lower barrier first,
- return quantiles,
- expected value after costs.

### 20.3 Deep learning
Later challengers only:
- LSTM,
- GRU,
- temporal CNN,
- temporal transformers.

Do not add deep learning until simpler models demonstrate economically useful signal.

---

## 21. Dynamic model selection / ensemble

Do not choose the single model that happened to perform best immediately before each trade.

Preferred process:
1. train on historical window,
2. evaluate walk-forward,
3. evaluate by regime,
4. calculate recent out-of-sample performance,
5. penalize instability/turnover/poor calibration,
6. calculate model weights,
7. aggregate forecasts.

Conceptually:

\[
Forecast_t = \sum_i w_{i,t}\ Forecast_{i,t}
\]

Weights may depend on:
- regime,
- recent OOS performance,
- forecast calibration,
- drawdown,
- stability,
- correlation among model errors.

Use bounds so one short-lived result cannot make a model dominate.

---

## 22. Champion / challenger governance

Maintain:
- Champion production model/ensemble.
- Challenger models evaluated in parallel.

A challenger does not replace the champion because of a few strong recent trades.

Promotion requires predetermined criteria across:
- multiple OOS windows,
- multiple regimes,
- drawdown,
- realistic costs,
- parameter stability,
- calibration,
- statistical/economic robustness.

Store all model versions in a model registry.

---

## 23. Meta-labeling

Research a secondary model that answers:

> Given that the primary engine produced a candidate signal, should this trade actually be executed?

Flow:
Primary signal -> meta-model -> execution probability / quality -> TRADE or NO_TRADE.

This supports selective trading.

---

## 24. Triple-barrier labeling

For suitable supervised-learning experiments, compare simple fixed-horizon labels against triple-barrier labels:
- upper take-profit barrier,
- lower stop-loss barrier,
- time barrier.

The label should reflect which barrier is hit first using data that would have been available in real time.

Prevent leakage when barriers overlap across train/test folds.

---

## 25. Entry engine

A candidate entry may require:
- valid regime,
- forecast above threshold,
- probability/confidence above threshold,
- expected edge exceeds estimated costs,
- volatility/risk acceptable,
- no hard macro/event restriction,
- no portfolio-level risk violation.

A valid output can be:
- `NO_TRADE`.

---

## 26. Stop-loss engine

Do not hard-code a permanent stop of 5% of price.

Preferred principle:
1. determine economically/statistically valid stop distance,
2. then size the position so loss at the stop equals the chosen risk budget.

Candidate stop inputs:
- ATR,
- forecast volatility,
- recent market structure,
- support/resistance,
- forecast return distribution / quantiles,
- regime.

General form:

\[
StopDistance_t =
f(ATR_t,\ \hat{\sigma}_t,\ structure_t,\ regime_t,\ distribution_t)
\]

A 5% number, if retained at all, should be a configurable hard loss/risk ceiling rather than the default market-distance rule.

---

## 27. Position sizing

Core principle:

\[
RiskAmount_t =
FXRiskCapital_t \times RiskPerTrade_t
\]

Then:

\[
PositionSize_t =
\frac{RiskAmount_t}
{StopDistance_t \times PipValue_t}
\]

Subject to:
- max leverage,
- max notional,
- max risk per trade,
- max portfolio risk,
- margin constraints,
- minimum/maximum executable size,
- current open risk,
- FX capital available.

Volatility affects stop/risk state; stop distance then affects position size.

---

## 28. Take-profit engine

Baseline:
- fixed risk/reward multiple.

Research challengers:
- ATR-based,
- volatility forecast,
- quantile forecast,
- market structure,
- support/resistance,
- probability of barrier hit.

Evaluate expected value:

\[
EV =
P(win)\cdot Gain -
P(loss)\cdot Loss -
Costs
\]

Research direct estimation of:

\[
P(TP\ before\ SL)
\]

---

## 29. Time stop

Because this is swing trading, the trade thesis has a horizon.

If expected price movement fails to materialize within a configured number of bars/days:
- close,
- reduce,
- or reassess according to an explicit rule.

Do not leave an expired thesis open indefinitely merely because neither price barrier was hit.

---

# PART D — DATA AND BACKTESTING

## 30. Data layers

Use a three-layer architecture:

### Raw / Bronze
Immutable source data.

Examples:
- prices,
- rates,
- macro releases,
- estimates,
- company data,
- news metadata/text.

### Clean / Silver
- timestamps normalized,
- time zones explicit,
- duplicates handled,
- corporate actions handled,
- missing data policy applied,
- release/availability times attached.

### Feature / Gold
- technical features,
- macro spreads,
- macro surprises,
- NLP scores,
- regimes,
- volatility estimates,
- model-ready matrices.

Prefer Parquet for local columnar storage initially, with DuckDB for analytical querying. PostgreSQL may be introduced later if the operational system requires it.

---

## 31. Point-in-time integrity

Every exogenous observation that can leak future information should distinguish where relevant:
- observation period,
- publication/release time,
- revision time,
- `available_to_model_time`.

Invariant:

\[
available\_to\_model\_time \le prediction\_time
\]

Examples:
- CPI cannot be used before its release.
- revised macro data must not overwrite the vintage that was known historically.
- news must not be available before publication.
- equity fundamental reports must respect filing/publication timestamps.

---

## 32. Backtesting engine

Two levels:

### 32.1 Research vectorized layer
Useful for rapid screening.

### 32.2 Final event-driven layer
Required for production-grade validation.

Must model as relevant:
- bid/ask spread,
- commissions,
- slippage,
- market/limit order behavior assumptions,
- FX financing/carry/swap,
- safe-asset return,
- delayed execution,
- position sizing,
- stop and take-profit execution,
- gaps,
- time stops,
- portfolio allocation,
- capital contributions,
- monthly rebalance,
- emergency de-risking,
- cash/unused FX capital,
- partial capital usage.

A simple `signal.shift(1) * return` result is not sufficient for final validation.

---

## 33. Validation

Use:
- chronological holdouts,
- walk-forward testing,
- purged cross-validation when overlapping labels apply,
- embargo,
- bootstrap / Monte Carlo where appropriate,
- transaction-cost sensitivity,
- parameter stability,
- regime breakdown,
- feature stability,
- stress testing.

Never use a random train/test split as the primary evidence for a time-series trading model.

---

## 34. Benchmarks

Every complex module must beat or justify itself relative to simpler alternatives.

Examples:
- CPPI classical,
- static 60/30/10,
- buy-and-hold/risk-balanced reference,
- simple volatility target,
- naive EUR/USD no-trade / random,
- simple momentum,
- moving-average trend,
- simple mean reversion,
- simple macro/yield-spread rule.

A complex AI/ML system that does not add robust net value after costs should not be promoted.

---

## 35. Metrics

### Portfolio/insurance
- CAGR,
- annualized volatility,
- maximum drawdown,
- downside deviation,
- Sharpe,
- Sortino,
- Calmar,
- CVaR / expected shortfall,
- floor breaches,
- capital-protection rate,
- cash-lock duration,
- upside/downside capture,
- turnover,
- costs.

### Trading
- net return,
- Sharpe,
- Sortino,
- Calmar,
- max drawdown,
- profit factor,
- expectancy,
- hit rate,
- average win/loss,
- win/loss ratio,
- exposure,
- turnover,
- average holding period,
- tail loss,
- cost burden,
- slippage.

### Predictive models
- calibration / reliability,
- Brier score for probabilities,
- precision/recall where relevant,
- ROC-AUC as a diagnostic only,
- correlation / information coefficient where relevant,
- error by regime,
- economic P&L after costs.

Accuracy alone is not a strategy objective.

---

# PART E — AUTOMATION, INFRASTRUCTURE AND EXECUTION

## 36. Initial technology stack

Python-first.

Candidates:
- pandas and/or Polars,
- NumPy,
- SciPy,
- statsmodels,
- scikit-learn,
- `arch`,
- XGBoost / LightGBM,
- PyPortfolioOpt and/or transparent in-house Black-Litterman implementation,
- DuckDB,
- Parquet,
- Streamlit for an initial dashboard,
- IBKR API in a later phase.

All dependencies should be pinned/reproducible.

---

## 37. Repository structure

Recommended initial structure:

```text
portfolio-system/
│
├── AGENTS.md
├── PROJECT_SPEC.md
├── ROADMAP.md
├── README.md
│
├── config/
│   ├── portfolio.yaml
│   ├── insurance.yaml
│   ├── equities.yaml
│   ├── fx.yaml
│   └── risk.yaml
│
├── data/
│   ├── raw/
│   ├── clean/
│   └── features/
│
├── src/
│   ├── data/
│   │   ├── market_data.py
│   │   ├── macro_data.py
│   │   ├── news_data.py
│   │   └── point_in_time.py
│   │
│   ├── portfolio/
│   │   ├── cppi.py
│   │   ├── tipp.py
│   │   ├── eppi.py
│   │   ├── floor_engine.py
│   │   ├── multiplier_engine.py
│   │   ├── black_litterman.py
│   │   └── allocator.py
│   │
│   ├── risk/
│   │   ├── volatility.py
│   │   ├── drawdown.py
│   │   ├── sizing.py
│   │   ├── stops.py
│   │   ├── limits.py
│   │   └── stress.py
│   │
│   ├── fx/
│   │   ├── features.py
│   │   ├── regimes.py
│   │   ├── signals.py
│   │   ├── ensemble.py
│   │   ├── meta_label.py
│   │   ├── trade_plan.py
│   │   └── execution.py
│   │
│   ├── models/
│   │   ├── econometric/
│   │   ├── ml/
│   │   └── registry/
│   │
│   ├── ai/
│   │   ├── schemas.py
│   │   ├── news_parser.py
│   │   ├── central_bank_nlp.py
│   │   └── equity_nlp.py
│   │
│   ├── backtest/
│   │   ├── vectorized.py
│   │   ├── event_engine.py
│   │   ├── costs.py
│   │   ├── validation.py
│   │   └── metrics.py
│   │
│   ├── audit/
│   │   └── events.py
│   │
│   └── broker/
│       └── ibkr.py
│
├── dashboard/
│   └── app.py
│
├── models/
├── reports/
├── notebooks/
│   └── research/
│
└── tests/
```

The exact layout may evolve, but domain boundaries must remain clear.

---

## 38. Scheduling concept

Indicative initial schedule:

| Process | Initial frequency |
|---|---|
| EUR/USD market update | 30 min during relevant market windows |
| technical features | 30 min |
| macro/news availability check | 30 min |
| FX inference | 30 min |
| volatility update | 4H or data-driven |
| regime inference | 4H or data-driven |
| ensemble-weight update | daily |
| retraining | weekly initially |
| full validation/model review | monthly |
| risk monitoring | daily minimum |
| CPPI ordinary rebalance | monthly |
| equity ordinary rebalance | monthly / bands |
| capital contribution | monthly |
| emergency-risk check | daily or more frequent if justified |

Do not blindly recalculate expensive models every 30 minutes if their input state has not changed.

GitHub Actions can be used for scheduled batch workflows where latency/uptime limitations are acceptable. Broker-connected live automation may later require a more persistent runtime.

---

## 39. Research -> execution ladder

No live automation directly from research.

Required stages:
1. Historical backtest.
2. Strict out-of-sample/walk-forward.
3. Shadow mode: generate real-time recommendations but send no orders.
4. IBKR paper trading.
5. Small live capital with manual confirmation.
6. Semi-automatic approval workflow.
7. Full automation only if explicitly approved after evidence.

---

# PART F — DASHBOARD AND AUDITABILITY

## 40. Dashboard purpose

Mobile-friendly control panel, not merely visualization.

Primary overview should answer quickly:
- total NAV,
- YTD / relevant return,
- current floor,
- high-water mark,
- cushion,
- multiplier,
- safe/risky allocation,
- equity allocation,
- FX capacity/current use,
- current drawdown,
- volatility/regime,
- next required action,
- whether an emergency condition exists.

---

## 41. Dashboard sections

Suggested tabs:
- Overview
- CPPI / Insurance
- Equities
- Black-Litterman
- EUR/USD
- Models
- Risk
- Backtests
- Trades
- Audit

EUR/USD trade card should be able to show:
- pair,
- state (`NO_TRADE`, `LONG`, `SHORT`),
- entry,
- stop,
- take-profit,
- risk amount,
- position size,
- regime,
- forecast/confidence,
- probability/expected value where available,
- model votes/weights,
- principal macro/technical drivers.

---

## 42. Model registry

Minimum fields:
- `model_id`,
- family,
- target,
- feature set/version,
- training start/end,
- training timestamp,
- hyperparameters,
- code commit hash,
- data version,
- OOS metrics,
- metrics by regime,
- cost assumptions,
- status (`RESEARCH`, `CHALLENGER`, `CHAMPION`, `RETIRED`),
- artifact location.

---

## 43. Decision audit trail

Every portfolio allocation decision should preserve:
- timestamp,
- NAV,
- contribution,
- HWM,
- floor,
- cushion,
- multiplier and components,
- allowed risky budget,
- current risky exposure,
- target safe/equity/FX weights,
- actual orders/rebalance action,
- config/model versions.

Every EUR/USD signal should preserve:
- signal ID,
- timestamp,
- all market-data timestamps,
- regime/probability,
- volatility state,
- model forecasts,
- ensemble weights,
- macro/NLP feature summary,
- intended entry/SL/TP,
- risk amount,
- position size,
- expected costs,
- final decision,
- model/config/code versions.

Goal:
Any historical decision can be reconstructed.

---

# PART G — SELF-IMPROVEMENT / AI GOVERNANCE

## 44. What "self-improving" means

It does **not** mean an AI is free to rewrite production code and deploy trades autonomously.

Preferred workflow:

Performance monitoring
-> drift detection
-> generate/research candidate model
-> backtest
-> walk-forward validation
-> compare with champion
-> human/review gate
-> controlled promotion.

Monitor:
- feature drift,
- prediction drift,
- calibration degradation,
- rolling performance,
- drawdown,
- regime-specific failure,
- turnover/cost drift.

---

## 45. Use of Codex

Codex should act as an engineering/research assistant.

Good task shape:
- implement one module,
- add tests,
- verify against a hand-computed case,
- compare challenger vs baseline,
- document assumptions.

Avoid:
- "build the whole system in one shot",
- allowing silent changes to financial requirements,
- letting one generated notebook become production architecture.

---

# PART H — PARAMETERS TO LEAVE CONFIGURABLE

Do not hard-code the following:
- initial capital,
- monthly contribution,
- safe-asset yield/series,
- reference safe/equity/FX percentages,
- risky equity/FX split,
- floor policy,
- protected fraction `alpha`,
- maximum drawdown protection target,
- base multiplier,
- min/max multiplier,
- volatility target,
- multiplier elasticity `gamma`,
- rebalance day/frequency,
- emergency thresholds,
- equity universe,
- Black-Litterman tau/risk aversion/view mappings,
- covariance estimator,
- transaction costs,
- FX leverage limits,
- max FX capital,
- risk per trade,
- max concurrent trades,
- stop methodology,
- TP methodology,
- model/feature windows,
- retraining frequency,
- champion promotion thresholds.

---

# PART I — OPEN RESEARCH QUESTIONS

The following are deliberately unresolved and should be tested rather than guessed:

1. What protected floor percentage (`alpha`) best balances protection and participation?
2. Should the TIPP floor ratchet on every new HWM or at rebalance dates only?
3. What is the appropriate base `m0` and min/max multiplier?
4. EWMA vs GARCH vs other forecast for portfolio-insurance risk?
5. What smooth functional form should map volatility/drawdown/regime to multiplier?
6. Does adaptive CPPI materially improve over simple CPPI/TIPP after costs?
7. Does EPPI add robust value?
8. What exact emergency-rebalance rules minimize breach risk without excessive turnover?
9. Is 75% equity / 25% FX the appropriate split inside the risky sleeve?
10. Should later risk budgeting treat the EUR/USD strategy return stream as a portfolio asset?
11. What stock universe and constraints are appropriate for BL?
12. How should systematic BL views be mapped into expected returns and confidence?
13. Which EUR/USD horizon is most stable: 4H, 1D, or mixed horizon?
14. Which model targets produce the most robust net trading edge?
15. Which regime model adds incremental value?
16. Does meta-labeling reduce bad trades enough to justify complexity?
17. Which stop/TP methodology maximizes risk-adjusted expectancy after costs?
18. Which news/NLP features remain stable out of sample?
19. What infrastructure is needed when moving from scheduled analysis to IBKR-connected automation?

---

# PART J — DEFINITION OF DONE FOR THE FINAL PRODUCT

A mature version is not "done" because it produces returns in a backtest.

It is done only when:
- data is point-in-time safe,
- all key financial formulas are unit-tested,
- portfolio-insurance variants are benchmarked,
- BL allocation is reproducible,
- EUR/USD signals survive walk-forward testing after realistic costs,
- risk constraints are enforced independently of model forecasts,
- all decisions are auditable,
- shadow mode works reliably,
- paper execution matches modeled assumptions within tolerance,
- failure modes are handled safely,
- dashboard accurately reflects live state,
- live execution, if ever enabled, has manual controls and kill switches.


## Verification and phase-1 model selection — 2026-09-23

All equations require sources and hand-checkable tests. A project composition
must be named as such and never passed off as a published canonical model.
The exact phase-1 identities are specified in docs/DYNAMIC_MODELS.md:

- Section 4.4 uses the normalized inverse-volatility dependence with gamma=1.
  Normalization, estimator, epsilon and bounds are explicit research policies.
- Section 4.5 benchmarks V4: volatility times a sourced drawdown-response factor.
  This composition is project-specific; it does not reproduce the source's MPC
  optimizer. The regime hook remains neutral; V5 follows the research ladder.
- Section 4.7 uses the discrete 2023 EPPI rule, with eta initialization and an
  unclipped raw cumulative state. No original-2008 replication is claimed.
- `conditional_cppi` remains an additional, distinct quantile-bound challenger.

These choices resolve the previously unspecified phase-1 implementations.
They do not change later empirical/OOS, regime-model, or live-deployment gates.
All defaults are illustrative, and no optimal financial parameters are asserted.
