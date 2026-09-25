# Phase 7 volatility and risk comparison

Synthetic chronological holdouts; costs/carry included. Forecast QLIKE uses subsequent squared returns, a noisy proxy.
Gap stress deliberately shows that stop orders do not guarantee the modeled budget.

| Fold | Rule | Volatility | Profile | Net return | Trades | Cost USD | Budget breaches |
|---|---|---|---|---:|---:|---:|---:|
| 1 | trend | realized | base | 0.000625 | 6 | 1.7604 | 0 |
| 1 | trend | ewma | base | 0.000594 | 6 | 1.7604 | 0 |
| 1 | trend | garch | base | 0.000611 | 6 | 1.7604 | 0 |
| 1 | mean_reversion | realized | base | -0.000317 | 4 | 1.1633 | 0 |
| 1 | rate_differential | realized | base | 0.001770 | 5 | 1.4625 | 0 |
| 1 | no_trade | realized | base | 0.000329 | 0 | 0.0000 | 0 |
| 1 | trend | realized | high_cost | -0.000607 | 5 | 14.2681 | 0 |
| 2 | trend | realized | base | 0.000432 | 6 | 1.6652 | 0 |
| 2 | trend | ewma | base | 0.000432 | 6 | 1.6652 | 0 |
| 2 | trend | garch | base | 0.000420 | 6 | 1.6652 | 0 |
| 2 | mean_reversion | realized | base | -0.000943 | 5 | 1.4299 | 0 |
| 2 | rate_differential | realized | base | -0.000761 | 6 | 1.6659 | 0 |
| 2 | no_trade | realized | base | 0.000219 | 0 | 0.0000 | 0 |
| 2 | trend | realized | high_cost | -0.001067 | 6 | 16.6517 | 0 |
| 3 | trend | realized | base | 0.000659 | 4 | 1.1634 | 0 |
| 3 | trend | ewma | base | 0.000649 | 4 | 1.1635 | 0 |
| 3 | trend | garch | base | 0.000657 | 4 | 1.1634 | 0 |
| 3 | mean_reversion | realized | base | -0.000143 | 4 | 1.1329 | 0 |
| 3 | rate_differential | realized | base | -0.000807 | 4 | 1.1311 | 0 |
| 3 | no_trade | realized | base | 0.000219 | 0 | 0.0000 | 0 |
| 3 | trend | realized | high_cost | -0.000369 | 4 | 11.6288 | 0 |
| stress | trend | realized | 3_percent_adverse_gap | -0.002224 | 4 | 1.1242 | 1 |
