# Phase 9 econometric comparison

Synthetic rolling refits in chronological holdouts. No tuning on holdouts. USD risk ledger includes fees/spread/slippage/carry/safe income.
ARIMAX is ARX(1); VAR shares that first equation on the same two-variable sample. VECM is disabled.
Conditional prediction errors use available forecasts; paired no-change errors use identical label timestamps.

| Fold | Model | Costs | Coverage | RMSE | Net return | Trades | Research status |
|---|---|---|---:|---:|---:|---:|---|
| 1 | no_change | base | 1.000 | 0.0014439824589270501 | 0.000110 | 0 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 1 | momentum | base | 1.000 | 0.0009417642080651656 | 0.000896 | 4 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 1 | ar | base | 1.000 | 0.000887289820699049 | 0.000896 | 4 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 1 | arimax | base | 1.000 | 0.0009485308684123708 | 0.000812 | 4 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 1 | var | base | 1.000 | 0.0009485308684123708 | 0.000812 | 4 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 1 | kalman | base | 1.000 | 0.0009070851969735312 | 0.000896 | 4 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 1 | markov_switching | base | 1.000 | 0.0012136270704407128 | 0.000646 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 1 | ar | high_cost | 1.000 | 0.000887289820699049 | 0.000110 | 0 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | no_change | base | 1.000 | 0.0011949872803013598 | 0.000110 | 0 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | momentum | base | 1.000 | 0.0008966298428057213 | 0.000622 | 4 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | ar | base | 1.000 | 0.0008291710343917533 | 0.000660 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | arimax | base | 1.000 | 0.0008424486739254029 | 0.000660 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | var | base | 1.000 | 0.0008424486739254028 | 0.000660 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | kalman | base | 1.000 | 0.0008555362462382048 | 0.000660 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | markov_switching | base | 1.000 | 0.0010890440869490506 | 0.000481 | 2 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 2 | ar | high_cost | 1.000 | 0.0008291710343917533 | 0.000110 | 0 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | no_change | base | 1.000 | 0.0012392137522480651 | 0.000110 | 0 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | momentum | base | 1.000 | 0.0009182383186535255 | 0.000676 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | ar | base | 1.000 | 0.0008591428692128727 | 0.000738 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | arimax | base | 1.000 | 0.0009626683571122297 | 0.000738 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | var | base | 1.000 | 0.0009626683571122296 | 0.000738 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | kalman | base | 1.000 | 0.0008995926456915143 | 0.000738 | 3 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | markov_switching | base | 1.000 | 0.0011266570406025583 | 0.000173 | 2 | ELIGIBLE_FOR_FURTHER_RESEARCH |
| 3 | ar | high_cost | 1.000 | 0.0008591428692128727 | 0.000110 | 0 | ELIGIBLE_FOR_FURTHER_RESEARCH |
