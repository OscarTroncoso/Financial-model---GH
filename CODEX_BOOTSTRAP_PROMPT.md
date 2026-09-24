# CODEX_BOOTSTRAP_PROMPT.md
# Initial prompt to give Codex

You are working on a new quantitative portfolio-management repository.

Before writing code:
1. Read `AGENTS.md`.
2. Read `PROJECT_SPEC.md` in full.
3. Read `ROADMAP.md`.
4. Treat `PROJECT_SPEC.md` as the authoritative financial/product specification.
5. Treat `ROADMAP.md` as the required implementation order and acceptance-gate document.
6. Do not implement the entire project at once.

We are starting with **Phase 0 and then Phase 1 only**.

Your immediate task is:

### Phase 0
- Inspect the repository.
- Propose the minimal Python package structure needed for Phase 1.
- Create configuration schemas/files for:
  - initial capital,
  - monthly contribution,
  - safe-asset return,
  - reference allocation,
  - floor policy,
  - CPPI multiplier parameters,
  - monthly rebalance rules,
  - emergency risk thresholds.
- Set up tests and a simple reproducible environment.
- Do not add broker integration, Black-Litterman, EUR/USD ML, AI/NLP, or a dashboard yet.

### Phase 1
Build a **Portfolio Insurance Laboratory** with:
- classical CPPI,
- HWM calculation,
- TIPP,
- drawdown-style floor,
- volatility-adaptive multiplier interface,
- adaptive multiplier factor interface,
- EPPI as a separate challenger interface,
- monthly contributions,
- monthly ordinary rebalancing,
- daily monitoring state,
- emergency de-risking hook/rule engine,
- safe-asset return,
- audit records,
- metrics and comparison report.

Important implementation constraints:
- Pure, testable financial functions wherever practical.
- No look-ahead.
- Parameters in config, not hard-coded.
- Financial units/conventions documented.
- Every formula has hand-checkable unit tests.
- The monthly contribution must enter before the monthly target allocation is computed.
- New capital should be usable to reduce drift before unnecessary sales.
- A monthly-rebalanced CPPI must not be presented as guaranteeing the floor.
- ML should not be implemented in Phase 1.
- EPPI should remain a challenger, not be silently merged into CPPI.
- TIPP and drawdown floors should share logic when mathematically equivalent rather than duplicating code.

Before coding, respond with:
1. files you plan to create/change,
2. financial assumptions that must be chosen for a first deterministic implementation,
3. a proposed Phase-1 API/data model,
4. the tests you will write,
5. any ambiguity you found in the specification.

Then implement only after that plan is clear.

At the end:
- run tests,
- produce a concise implementation summary,
- list assumptions,
- list unresolved research parameters,
- do not begin Phase 2 automatically.
