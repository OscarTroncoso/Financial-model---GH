# AGENTS.md

## Project purpose
Build a modular, auditable portfolio-management and swing-trading system in Python. The system combines:
1. Portfolio insurance / capital protection (CPPI family).
2. Long-term equity allocation (Black-Litterman).
3. Tactical EUR/USD swing trading.
4. Risk management, backtesting, monitoring, model governance, and later IBKR integration.

The authoritative product requirements are in `PROJECT_SPEC.md`.
The execution sequence and acceptance gates are in `ROADMAP.md`.

## Non-negotiable engineering rules
- Do not change financial logic silently. If a requirement is ambiguous, state the assumption before coding.
- Do not implement a later phase before the acceptance criteria of the current phase pass.
- Keep modules small, typed, testable, and replaceable.
- Never hard-code portfolio parameters that belong in configuration.
- Every financial calculation must have unit tests with hand-checkable examples.
- Every backtest must be point-in-time safe and must prevent look-ahead bias.
- Data available to a model at time `t` must have `available_to_model_time <= t`.
- Treat transaction costs, spread, slippage, financing/carry, and cash/safe-asset returns explicitly.
- Recalculation is not the same as rebalancing.
- Model outputs must be reproducible from saved inputs/config/model version.
- Preserve an audit trail for every allocation decision and every FX signal.
- ML/AI may influence estimates and risk modifiers, but hard portfolio-risk limits must not be overridable by ML.
- "NO TRADE" is a valid EUR/USD output.
- Do not automate live brokerage execution until shadow mode and paper trading acceptance gates pass.

## Quant/research rules
- Verify every model against accessible primary sources and record exact equations, units, assumptions, and hand-calculated tests in `docs/MODELS.md`. Never invent a missing formula or present a project convention as a published model. Keep unverified models disabled and their phase gates open.
- Always establish a simple benchmark before adding complexity.
- Use walk-forward/out-of-sample evaluation; no random train/test split for time-series trading evaluation.
- Compare sophisticated models against simple baselines after realistic costs.
- Avoid optimizing a model only on Sharpe. Use the metric sets specified in `PROJECT_SPEC.md`.
- Do not use VECM unless cointegration is demonstrated and economically defensible.
- Deep learning is a later-phase challenger, not a default.
- Never use an LLM to directly output an unaudited BUY/SELL decision. LLM outputs must first become structured features or documented research inputs.

## Portfolio rules
- Current provisional strategic reference allocation is 60% safe / 30% equities / 10% EUR/USD capacity. These are configurable reference values, not immutable actual weights.
- CPPI/TIPP determines the permitted risky budget.
- Within the risky budget, the provisional reference split is 75% equity / 25% FX capacity, subject to later research.
- Unused FX capacity remains in the safe sleeve.
- Long-term equities are strategic holdings; Black-Litterman determines target weights, not short-term market timing.
- Ordinary portfolio rebalance: monthly.
- Risk monitoring: at least daily.
- Emergency de-risking may occur between monthly rebalances when hard risk conditions are breached.
- Monthly contributions enter the system before the monthly allocation calculation and should be used first to reduce drift before unnecessary sales.

## Coding conventions
- Python-first.
- Use clear domain names: `portfolio_value`, `floor`, `high_water_mark`, `cushion`, `risky_budget`, `multiplier`, etc.
- Prefer pure functions for financial formulas.
- Separate research notebooks from production modules.
- Keep configuration under `config/`.
- Tests under `tests/`.
- Never make a production result depend on notebook state.
- Add docstrings explaining financial meaning, assumptions, units, and edge cases.

## Change procedure
For each task:
1. Read the relevant section of `PROJECT_SPEC.md`.
2. Read the current phase and acceptance criteria in `ROADMAP.md`.
3. State the implementation plan briefly.
4. Implement the smallest coherent change.
5. Add/update tests.
6. Run the relevant test suite.
7. Summarize files changed, tests run, assumptions made, and any unresolved risk.

## Safety / deployment
- No secrets, broker credentials, or API keys in the repository.
- Use environment variables or secret stores.
- Live-order routing must have explicit kill switches, exposure limits, and idempotency protections.
- A failed data update or failed model inference must fail safe, not create a trade.
