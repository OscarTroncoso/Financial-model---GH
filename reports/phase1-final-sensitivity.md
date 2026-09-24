# Phase 1 synthetic sensitivity suite

Nine predefined profiles; ten synthetic paths and eight models per profile.
Ranges are across heterogeneous stresses, not statistical confidence intervals.
Costs and breach counts are summed across paths only as diagnostics.
No optimization, historical data, OOS evidence, or strategy promotion.

| Profile | Model | Min TWR | Max TWR | Worst drawdown | Breach observations | Costs EUR |
|---|---|---:|---:|---:|---:|---:|
| baseline | adaptive | -7.67% | 59.21% | 8.04% | 0 | 228.63 |
| baseline | conditional_cppi | -12.62% | 84.85% | 15.44% | 0 | 235.71 |
| baseline | cppi | -28.11% | 53.66% | 29.92% | 104 | 142.17 |
| baseline | drawdown | -28.11% | 43.88% | 29.92% | 104 | 142.12 |
| baseline | eppi | -28.11% | 55.19% | 29.92% | 104 | 42.98 |
| baseline | static | -17.03% | 28.21% | 20.02% | 0 | 30.61 |
| baseline | tipp | -28.11% | 43.88% | 29.92% | 104 | 142.12 |
| baseline | volatility_adaptive | -7.67% | 61.04% | 8.04% | 0 | 228.70 |
| zero_cost | adaptive | -7.61% | 61.64% | 7.98% | 0 | 0.00 |
| zero_cost | conditional_cppi | -12.49% | 85.25% | 15.36% | 0 | 0.00 |
| zero_cost | cppi | -28.07% | 54.17% | 29.92% | 104 | 0.00 |
| zero_cost | drawdown | -28.07% | 44.05% | 29.92% | 104 | 0.00 |
| zero_cost | eppi | -28.07% | 55.31% | 29.92% | 104 | 0.00 |
| zero_cost | static | -17.01% | 28.24% | 20.02% | 0 | 0.00 |
| zero_cost | tipp | -28.07% | 44.05% | 29.92% | 104 | 0.00 |
| zero_cost | volatility_adaptive | -7.61% | 61.64% | 7.98% | 0 | 0.00 |
| high_cost | adaptive | -8.18% | 57.46% | 8.55% | 0 | 906.94 |
| high_cost | conditional_cppi | -13.00% | 83.65% | 15.69% | 0 | 935.66 |
| high_cost | cppi | -28.22% | 54.16% | 29.92% | 104 | 563.65 |
| high_cost | drawdown | -28.22% | 43.37% | 29.92% | 104 | 564.72 |
| high_cost | eppi | -28.22% | 54.84% | 29.92% | 104 | 171.78 |
| high_cost | static | -17.10% | 28.11% | 20.02% | 0 | 122.36 |
| high_cost | tipp | -28.22% | 43.37% | 29.92% | 104 | 564.72 |
| high_cost | volatility_adaptive | -8.18% | 59.25% | 8.55% | 0 | 907.22 |
| floor_90 | adaptive | -6.73% | 28.25% | 7.03% | 0 | 103.27 |
| floor_90 | conditional_cppi | -6.73% | 37.47% | 7.71% | 0 | 111.90 |
| floor_90 | cppi | -13.34% | 26.60% | 15.04% | 104 | 55.05 |
| floor_90 | drawdown | -13.34% | 16.79% | 15.04% | 104 | 34.42 |
| floor_90 | eppi | -13.34% | 25.22% | 15.04% | 104 | 20.28 |
| floor_90 | static | -17.03% | 28.21% | 20.02% | 197 | 30.61 |
| floor_90 | tipp | -13.34% | 16.79% | 15.04% | 104 | 34.42 |
| floor_90 | volatility_adaptive | -6.73% | 28.78% | 7.03% | 0 | 103.45 |
| multiplier_2 | adaptive | -7.67% | 55.81% | 8.04% | 0 | 220.64 |
| multiplier_2 | conditional_cppi | -12.62% | 84.85% | 15.44% | 0 | 235.71 |
| multiplier_2 | cppi | -18.26% | 29.79% | 20.02% | 0 | 60.98 |
| multiplier_2 | drawdown | -18.26% | 18.91% | 20.02% | 1 | 43.98 |
| multiplier_2 | eppi | -28.11% | 55.19% | 29.92% | 104 | 42.98 |
| multiplier_2 | static | -17.03% | 28.21% | 20.02% | 0 | 30.61 |
| multiplier_2 | tipp | -18.26% | 18.91% | 20.02% | 1 | 43.98 |
| multiplier_2 | volatility_adaptive | -7.67% | 55.81% | 8.04% | 0 | 220.64 |
| volatility_target_10 | adaptive | -7.67% | 55.81% | 8.04% | 0 | 220.64 |
| volatility_target_10 | conditional_cppi | -12.62% | 84.85% | 15.44% | 0 | 235.71 |
| volatility_target_10 | cppi | -28.11% | 53.66% | 29.92% | 104 | 142.17 |
| volatility_target_10 | drawdown | -28.11% | 43.88% | 29.92% | 104 | 142.12 |
| volatility_target_10 | eppi | -28.11% | 55.19% | 29.92% | 104 | 42.98 |
| volatility_target_10 | static | -17.03% | 28.21% | 20.02% | 0 | 30.61 |
| volatility_target_10 | tipp | -28.11% | 43.88% | 29.92% | 104 | 142.12 |
| volatility_target_10 | volatility_adaptive | -7.67% | 55.81% | 8.04% | 0 | 220.64 |
| eppi_exponent_3 | adaptive | -7.67% | 59.21% | 8.04% | 0 | 228.63 |
| eppi_exponent_3 | conditional_cppi | -12.62% | 84.85% | 15.44% | 0 | 235.71 |
| eppi_exponent_3 | cppi | -28.11% | 53.66% | 29.92% | 104 | 142.17 |
| eppi_exponent_3 | drawdown | -28.11% | 43.88% | 29.92% | 104 | 142.12 |
| eppi_exponent_3 | eppi | -28.11% | 59.41% | 29.92% | 104 | 46.62 |
| eppi_exponent_3 | static | -17.03% | 28.21% | 20.02% | 0 | 30.61 |
| eppi_exponent_3 | tipp | -28.11% | 43.88% | 29.92% | 104 | 142.12 |
| eppi_exponent_3 | volatility_adaptive | -7.67% | 61.04% | 8.04% | 0 | 228.70 |
| monthly_ratchet | adaptive | -7.67% | 59.21% | 8.04% | 0 | 228.63 |
| monthly_ratchet | conditional_cppi | -12.62% | 84.85% | 15.44% | 0 | 235.71 |
| monthly_ratchet | cppi | -28.11% | 53.66% | 29.92% | 104 | 142.17 |
| monthly_ratchet | drawdown | -28.11% | 43.88% | 29.92% | 104 | 142.03 |
| monthly_ratchet | eppi | -28.11% | 55.19% | 29.92% | 104 | 42.91 |
| monthly_ratchet | static | -17.03% | 28.21% | 20.02% | 0 | 30.61 |
| monthly_ratchet | tipp | -28.11% | 43.88% | 29.92% | 104 | 142.03 |
| monthly_ratchet | volatility_adaptive | -7.67% | 61.04% | 8.04% | 0 | 228.70 |
| no_optional_emergency | adaptive | -19.79% | 30.02% | 20.14% | 0 | 71.72 |
| no_optional_emergency | conditional_cppi | -21.62% | 47.42% | 28.39% | 20 | 78.04 |
| no_optional_emergency | cppi | -26.44% | 43.68% | 34.32% | 105 | 49.14 |
| no_optional_emergency | drawdown | -26.99% | 37.94% | 29.92% | 105 | 45.08 |
| no_optional_emergency | eppi | -26.99% | 45.73% | 29.92% | 105 | 30.51 |
| no_optional_emergency | static | -17.03% | 28.21% | 20.02% | 0 | 30.61 |
| no_optional_emergency | tipp | -26.99% | 37.94% | 29.92% | 105 | 45.08 |
| no_optional_emergency | volatility_adaptive | -21.62% | 29.25% | 21.83% | 14 | 66.04 |
