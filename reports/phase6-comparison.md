# Phase 6 EUR/USD chronological baseline comparison

Synthetic engineering evidence; fixed parameters chosen before all folds, no tuning or random split.
Independent holdouts start flat and liquidate at their precommitted final close. USD collateral ledger.

| Fold | Rule | Costs | Net return | Max drawdown | Trades | Cost USD | Carry USD |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | no_trade | base | 0.000329 | 0.000000 | 0 | 0.0000 | 0.0000 |
| 1 | trend | base | -0.000288 | 0.000713 | 3 | 0.9007 | -0.3373 |
| 1 | trend | high_cost | -0.001099 | 0.001116 | 3 | 9.0035 | -0.3371 |
| 1 | mean_reversion | base | -0.000486 | 0.000761 | 2 | 0.6011 | 0.0380 |
| 1 | rate_differential | base | -0.000442 | 0.001260 | 2 | 0.6007 | 0.0775 |
| 2 | no_trade | base | 0.000329 | 0.000000 | 0 | 0.0000 | 0.0000 |
| 2 | trend | base | 0.000974 | 0.000537 | 3 | 0.9004 | 0.0349 |
| 2 | trend | high_cost | 0.000163 | 0.001048 | 3 | 9.0006 | 0.0349 |
| 2 | mean_reversion | base | -0.000579 | 0.000615 | 2 | 0.5998 | -0.0616 |
| 2 | rate_differential | base | 0.002134 | 0.000127 | 2 | 0.6001 | -0.0311 |
| 3 | no_trade | base | 0.000219 | 0.000000 | 0 | 0.0000 | 0.0000 |
| 3 | trend | base | 0.000445 | 0.000987 | 2 | 0.5981 | -0.1697 |
| 3 | trend | high_cost | -0.000094 | 0.001256 | 2 | 5.9797 | -0.1697 |
| 3 | mean_reversion | base | -0.001190 | 0.001200 | 2 | 0.5994 | -0.0759 |
| 3 | rate_differential | base | -0.001002 | 0.001633 | 1 | 0.2983 | -0.2610 |
