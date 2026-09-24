# Synthetic portfolio insurance comparison

Mechanical tests only: no historical/OOS evidence and no guaranteed floor.
All mandatory variants are included; see docs/DYNAMIC_MODELS.md for exact identities.
Static = monthly constant-mix aggregate risky proxy, without emergency overlay.
All other models use configured emergency policy. Pure strategy tests can disable it.
conditional_cppi uses a published quantile bound plus a rolling Gaussian baseline; not a probability guarantee.
It holds safe during warm-up and waits for the next monthly decision before entering.
TIPP and drawdown coincide when alpha = 1 - maximum_drawdown.

| Synthetic path | Model | Net TWR | Max drawdown | Breach observations | Costs EUR |
|---|---|---:|---:|---:|---:|
| steady_growth | static | 6.05% | 0.01% | 0 | 2.00 |
| steady_growth | cppi | 9.35% | 0.02% | 0 | 3.96 |
| steady_growth | tipp | 8.36% | 0.02% | 0 | 3.00 |
| steady_growth | drawdown | 8.36% | 0.02% | 0 | 3.00 |
| steady_growth | conditional_cppi | 11.04% | 0.04% | 0 | 5.26 |
| steady_growth | volatility_adaptive | 11.04% | 0.04% | 0 | 5.26 |
| steady_growth | adaptive | 11.04% | 0.04% | 0 | 5.26 |
| steady_growth | eppi | 8.61% | 0.02% | 0 | 3.21 |
| prolonged_bear | static | -17.03% | 17.03% | 0 | 2.59 |
| prolonged_bear | cppi | -14.02% | 14.02% | 0 | 20.83 |
| prolonged_bear | tipp | -14.26% | 14.26% | 0 | 20.57 |
| prolonged_bear | drawdown | -14.26% | 14.26% | 0 | 20.57 |
| prolonged_bear | conditional_cppi | -7.55% | 7.91% | 0 | 43.10 |
| prolonged_bear | volatility_adaptive | -7.55% | 7.91% | 0 | 43.10 |
| prolonged_bear | adaptive | -7.55% | 7.91% | 0 | 43.10 |
| prolonged_bear | eppi | 1.44% | 0.00% | 0 | 0.00 |
| fast_crash_rebound | static | 28.21% | 13.62% | 0 | 2.76 |
| fast_crash_rebound | cppi | -4.73% | 9.21% | 0 | 7.80 |
| fast_crash_rebound | tipp | -4.90% | 9.21% | 0 | 7.63 |
| fast_crash_rebound | drawdown | -4.90% | 9.21% | 0 | 7.63 |
| fast_crash_rebound | conditional_cppi | -12.62% | 15.44% | 0 | 11.11 |
| fast_crash_rebound | volatility_adaptive | 4.95% | 0.03% | 0 | 5.25 |
| fast_crash_rebound | adaptive | 4.95% | 0.03% | 0 | 5.25 |
| fast_crash_rebound | eppi | -4.00% | 9.21% | 0 | 8.64 |
| overnight_gap | static | -12.08% | 20.02% | 0 | 2.65 |
| overnight_gap | cppi | -28.11% | 29.92% | 104 | 4.53 |
| overnight_gap | tipp | -28.11% | 29.92% | 104 | 4.53 |
| overnight_gap | drawdown | -28.11% | 29.92% | 104 | 4.53 |
| overnight_gap | conditional_cppi | 13.70% | 0.04% | 0 | 5.28 |
| overnight_gap | volatility_adaptive | 13.70% | 0.04% | 0 | 5.28 |
| overnight_gap | adaptive | 13.70% | 0.04% | 0 | 5.28 |
| overnight_gap | eppi | -28.11% | 29.92% | 104 | 4.53 |
| volatility_spike | static | 1.47% | 4.78% | 0 | 2.14 |
| volatility_spike | cppi | 7.79% | 4.40% | 0 | 10.42 |
| volatility_spike | tipp | 8.14% | 3.67% | 0 | 9.52 |
| volatility_spike | drawdown | 8.14% | 3.67% | 0 | 9.52 |
| volatility_spike | conditional_cppi | 4.45% | 6.04% | 0 | 15.33 |
| volatility_spike | volatility_adaptive | 4.95% | 0.03% | 0 | 5.25 |
| volatility_spike | adaptive | 4.95% | 0.03% | 0 | 5.25 |
| volatility_spike | eppi | 8.65% | 3.65% | 0 | 10.31 |
| early_losses | static | 14.34% | 14.08% | 0 | 3.05 |
| early_losses | cppi | 53.66% | 6.30% | 0 | 15.68 |
| early_losses | tipp | 38.09% | 6.30% | 0 | 13.90 |
| early_losses | drawdown | 38.09% | 6.30% | 0 | 13.90 |
| early_losses | conditional_cppi | 84.85% | 3.06% | 0 | 15.09 |
| early_losses | volatility_adaptive | 61.04% | 3.06% | 0 | 24.02 |
| early_losses | adaptive | 59.21% | 3.06% | 0 | 23.95 |
| early_losses | eppi | 45.73% | 0.01% | 0 | 2.85 |
| late_losses | static | 13.34% | 14.59% | 0 | 3.16 |
| late_losses | cppi | 43.51% | 19.05% | 0 | 12.58 |
| late_losses | tipp | 43.88% | 4.91% | 0 | 16.80 |
| late_losses | drawdown | 43.88% | 4.91% | 0 | 16.80 |
| late_losses | conditional_cppi | 54.14% | 5.42% | 0 | 27.59 |
| late_losses | volatility_adaptive | 54.14% | 5.42% | 0 | 27.59 |
| late_losses | adaptive | 54.14% | 5.42% | 0 | 27.59 |
| late_losses | eppi | 55.19% | 4.06% | 0 | 10.28 |
| negative_safe_return | static | -5.55% | 5.55% | 0 | 2.17 |
| negative_safe_return | cppi | -6.93% | 6.93% | 0 | 3.49 |
| negative_safe_return | tipp | -6.93% | 6.93% | 0 | 3.49 |
| negative_safe_return | drawdown | -6.93% | 6.93% | 0 | 3.49 |
| negative_safe_return | conditional_cppi | -1.25% | 1.25% | 0 | 0.00 |
| negative_safe_return | volatility_adaptive | -1.25% | 1.25% | 0 | 0.00 |
| negative_safe_return | adaptive | -1.25% | 1.25% | 0 | 0.00 |
| negative_safe_return | eppi | -1.25% | 1.25% | 0 | 0.00 |
| high_safe_return | static | 2.25% | 0.00% | 0 | 2.11 |
| high_safe_return | cppi | 1.43% | 0.01% | 0 | 3.34 |
| high_safe_return | tipp | 1.49% | 0.01% | 0 | 3.15 |
| high_safe_return | drawdown | 1.49% | 0.01% | 0 | 3.15 |
| high_safe_return | conditional_cppi | 0.66% | 0.03% | 0 | 5.28 |
| high_safe_return | volatility_adaptive | 0.66% | 0.03% | 0 | 5.28 |
| high_safe_return | adaptive | 0.66% | 0.03% | 0 | 5.28 |
| high_safe_return | eppi | 1.49% | 0.01% | 0 | 3.15 |
| large_deposits_in_drawdown | static | -16.91% | 16.91% | 0 | 7.97 |
| large_deposits_in_drawdown | cppi | -15.16% | 15.16% | 0 | 59.54 |
| large_deposits_in_drawdown | tipp | -15.16% | 15.16% | 0 | 59.53 |
| large_deposits_in_drawdown | drawdown | -15.16% | 15.16% | 0 | 59.53 |
| large_deposits_in_drawdown | conditional_cppi | -7.67% | 8.04% | 0 | 107.67 |
| large_deposits_in_drawdown | volatility_adaptive | -7.67% | 8.04% | 0 | 107.67 |
| large_deposits_in_drawdown | adaptive | -7.67% | 8.04% | 0 | 107.67 |
| large_deposits_in_drawdown | eppi | 1.44% | 0.00% | 0 | 0.00 |

Full metric definitions: source/metrics.py. Each JSON preserves inputs and every decision.
Code SHA256: `2060253c256302aad5cf8658fb8808b1d98c1f77d4384c4ca4f8a7c0fd3bcaf3`.
