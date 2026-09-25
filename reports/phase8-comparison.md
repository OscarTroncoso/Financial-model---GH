# Phase 8: entry-decision regime attribution

Synthetic chronological holdouts; trade P&L includes costs and carry. Safe income is separate.
Conditional trade groups, not independently investable portfolios. No profitability claim.

| Fold | Model | Cost | Method | State | Trades | Net P&L USD | Costs USD |
|---|---|---|---|---|---:|---:|---:|
| 1 | trend | base | hmm | variance_rank_0 | 2 | 1.8418 | 0.5671 |
| 1 | trend | base | hmm | variance_rank_1 | 4 | 1.1143 | 1.1933 |
| 1 | trend | base | rule | down_medium | 2 | 3.1064 | 0.5968 |
| 1 | trend | base | rule | sideways_medium | 2 | -1.9921 | 0.5965 |
| 1 | trend | base | rule | up_medium | 2 | 1.8418 | 0.5671 |
| 1 | mean_reversion | base | hmm | variance_rank_0 | 2 | -3.2753 | 0.5668 |
| 1 | mean_reversion | base | hmm | variance_rank_1 | 2 | -3.1845 | 0.5965 |
| 1 | mean_reversion | base | rule | down_medium | 2 | -3.1845 | 0.5965 |
| 1 | mean_reversion | base | rule | up_medium | 2 | -3.2753 | 0.5668 |
| 1 | rate_differential | base | hmm | variance_rank_0 | 2 | 0.4732 | 0.5676 |
| 1 | rate_differential | base | hmm | variance_rank_1 | 3 | 13.9398 | 0.8949 |
| 1 | rate_differential | base | rule | down_medium | 2 | 8.7491 | 0.5959 |
| 1 | rate_differential | base | rule | sideways_medium | 1 | 5.1907 | 0.2990 |
| 1 | rate_differential | base | rule | up_medium | 2 | 0.4732 | 0.5676 |
| 1 | trend | high_cost | hmm | variance_rank_0 | 1 | 0.5522 | 2.6672 |
| 1 | trend | high_cost | hmm | variance_rank_1 | 4 | -9.9121 | 11.6008 |
| 1 | trend | high_cost | rule | down_medium | 2 | -2.5514 | 5.6358 |
| 1 | trend | high_cost | rule | sideways_medium | 2 | -7.3607 | 5.9650 |
| 1 | trend | high_cost | rule | up_medium | 1 | 0.5522 | 2.6672 |
| 2 | trend | base | hmm | variance_rank_0 | 5 | 4.8854 | 1.3969 |
| 2 | trend | base | hmm | variance_rank_1 | 1 | -2.7603 | 0.2683 |
| 2 | trend | base | rule | down_medium | 2 | 5.7609 | 0.5954 |
| 2 | trend | base | rule | sideways_medium | 1 | -2.7236 | 0.2664 |
| 2 | trend | base | rule | up_medium | 3 | -0.9123 | 0.8034 |
| 2 | mean_reversion | base | hmm | variance_rank_0 | 4 | -9.9989 | 1.1617 |
| 2 | mean_reversion | base | hmm | variance_rank_1 | 1 | -1.6176 | 0.2682 |
| 2 | mean_reversion | base | rule | down_medium | 3 | -7.2533 | 0.8942 |
| 2 | mean_reversion | base | rule | up_medium | 2 | -4.3631 | 0.5356 |
| 2 | rate_differential | base | hmm | variance_rank_0 | 5 | -7.0464 | 1.3976 |
| 2 | rate_differential | base | hmm | variance_rank_1 | 1 | -2.7603 | 0.2683 |
| 2 | rate_differential | base | rule | down_medium | 2 | -6.1709 | 0.5961 |
| 2 | rate_differential | base | rule | sideways_medium | 1 | -2.7236 | 0.2664 |
| 2 | rate_differential | base | rule | up_medium | 3 | -0.9123 | 0.8034 |
| 2 | trend | high_cost | hmm | variance_rank_0 | 5 | -7.6866 | 13.9689 |
| 2 | trend | high_cost | hmm | variance_rank_1 | 1 | -5.1749 | 2.6828 |
| 2 | trend | high_cost | rule | down_medium | 2 | 0.4025 | 5.9538 |
| 2 | trend | high_cost | rule | sideways_medium | 1 | -5.1212 | 2.6640 |
| 2 | trend | high_cost | rule | up_medium | 3 | -8.1428 | 8.0340 |
| 3 | trend | base | hmm | variance_rank_1 | 4 | 4.4010 | 1.1634 |
| 3 | trend | base | rule | down_medium | 1 | -3.0135 | 0.2975 |
| 3 | trend | base | rule | sideways_medium | 2 | 3.7418 | 0.5979 |
| 3 | trend | base | rule | up_medium | 1 | 3.6727 | 0.2680 |
| 3 | mean_reversion | base | hmm | variance_rank_1 | 4 | -3.6212 | 1.1329 |
| 3 | mean_reversion | base | rule | down_medium | 1 | 0.7752 | 0.2973 |
| 3 | mean_reversion | base | rule | up_medium | 3 | -4.3964 | 0.8356 |
| 3 | rate_differential | base | hmm | variance_rank_1 | 4 | -10.2605 | 1.1311 |
| 3 | rate_differential | base | rule | down_medium | 1 | -1.7463 | 0.2969 |
| 3 | rate_differential | base | rule | up_medium | 3 | -8.5142 | 0.8342 |
| 3 | trend | high_cost | hmm | variance_rank_1 | 4 | -5.8839 | 11.6288 |
| 3 | trend | high_cost | rule | down_medium | 1 | -5.6912 | 2.9752 |
| 3 | trend | high_cost | rule | sideways_medium | 2 | -2.3236 | 5.9780 |
| 3 | trend | high_cost | rule | up_medium | 1 | 2.1309 | 2.6756 |
