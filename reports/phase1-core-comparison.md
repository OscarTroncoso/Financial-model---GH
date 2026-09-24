# Synthetic portfolio insurance comparison

Mechanical tests only: no historical/OOS evidence and no guaranteed floor.
Phase 1 gate remains OPEN: volatility-adaptive, adaptive and EPPI are blocked.
Static = monthly constant-mix aggregate risky proxy, without emergency overlay.
All other models use configured emergency policy. Pure strategy tests can disable it.
TIPP and drawdown coincide when alpha = 1 - maximum_drawdown.

| Synthetic path | Model | Net TWR | Max drawdown | Breach observations | Costs EUR |
|---|---|---:|---:|---:|---:|
| steady_growth | static | 6.05% | 0.01% | 0 | 2.00 |
| steady_growth | cppi | 9.35% | 0.02% | 0 | 3.96 |
| steady_growth | tipp | 8.36% | 0.02% | 0 | 3.00 |
| steady_growth | drawdown | 8.36% | 0.02% | 0 | 3.00 |
| prolonged_bear | static | -17.03% | 17.03% | 0 | 2.59 |
| prolonged_bear | cppi | -14.02% | 14.02% | 0 | 20.83 |
| prolonged_bear | tipp | -14.26% | 14.26% | 0 | 20.57 |
| prolonged_bear | drawdown | -14.26% | 14.26% | 0 | 20.57 |
| fast_crash_rebound | static | 28.21% | 13.62% | 0 | 2.76 |
| fast_crash_rebound | cppi | -4.73% | 9.21% | 0 | 7.80 |
| fast_crash_rebound | tipp | -4.90% | 9.21% | 0 | 7.63 |
| fast_crash_rebound | drawdown | -4.90% | 9.21% | 0 | 7.63 |
| overnight_gap | static | -12.08% | 20.02% | 0 | 2.65 |
| overnight_gap | cppi | -28.11% | 29.92% | 104 | 4.53 |
| overnight_gap | tipp | -28.11% | 29.92% | 104 | 4.53 |
| overnight_gap | drawdown | -28.11% | 29.92% | 104 | 4.53 |
| volatility_spike | static | 1.47% | 4.78% | 0 | 2.14 |
| volatility_spike | cppi | 7.79% | 4.40% | 0 | 10.42 |
| volatility_spike | tipp | 8.14% | 3.67% | 0 | 9.52 |
| volatility_spike | drawdown | 8.14% | 3.67% | 0 | 9.52 |
| early_losses | static | 14.34% | 14.08% | 0 | 3.05 |
| early_losses | cppi | 53.66% | 6.30% | 0 | 15.68 |
| early_losses | tipp | 38.09% | 6.30% | 0 | 13.90 |
| early_losses | drawdown | 38.09% | 6.30% | 0 | 13.90 |
| late_losses | static | 13.34% | 14.59% | 0 | 3.16 |
| late_losses | cppi | 43.51% | 19.05% | 0 | 12.58 |
| late_losses | tipp | 43.88% | 4.91% | 0 | 16.80 |
| late_losses | drawdown | 43.88% | 4.91% | 0 | 16.80 |
| negative_safe_return | static | -5.55% | 5.55% | 0 | 2.17 |
| negative_safe_return | cppi | -6.93% | 6.93% | 0 | 3.49 |
| negative_safe_return | tipp | -6.93% | 6.93% | 0 | 3.49 |
| negative_safe_return | drawdown | -6.93% | 6.93% | 0 | 3.49 |
| high_safe_return | static | 2.25% | 0.00% | 0 | 2.11 |
| high_safe_return | cppi | 1.43% | 0.01% | 0 | 3.34 |
| high_safe_return | tipp | 1.49% | 0.01% | 0 | 3.15 |
| high_safe_return | drawdown | 1.49% | 0.01% | 0 | 3.15 |
| large_deposits_in_drawdown | static | -16.91% | 16.91% | 0 | 7.97 |
| large_deposits_in_drawdown | cppi | -15.16% | 15.16% | 0 | 59.54 |
| large_deposits_in_drawdown | tipp | -15.16% | 15.16% | 0 | 59.53 |
| large_deposits_in_drawdown | drawdown | -15.16% | 15.16% | 0 | 59.53 |

Full metric definitions: [metrics.py](../src/portfolio_lab/metrics.py). Each JSON preserves inputs and every decision.
Code SHA256: `ef667d9ee11aee7e79e13f83afa7308ad89327c85bfaa19dc6dbab3c9f2cd055`.

Local full bundle: [inputs, events and manifest](runs/phase1-core-20260923/). Generated full bundles are ignored by Git; recreate them with the README command.
