# 009. Intra-period safety checks

Date: 2026-11-05   Decision: [0028](../decisions/0028-intra-period-safety-checks.md)   Code: working tree on top of `92ccc47`
Command: `uv run python run_safety_experiments.py --exp d028`   Raw: `results/experiments/safety/{flat,hier}_{periods,stress}.csv`

## Question
The shield acts only at rebalances (every 21 trading days). Does also checking every day, and cutting exposure when needed, reduce safety violations enough to be worth the extra trading and code?

## Variants
| Variant | Config | What it does |
|---|---|---|
| no shield | `safety=False` | Monitor only, portfolio untouched |
| rebalance+uniform | `safety=True` | Shield acts at each rebalance (decision 0025) |
| daily+uniform | `safety=True, safety_daily=True` | Same, plus every day: re-run `supervise` on data before that day; if it asks for less exposure than held, cut to it and pay costs. Never re-risks until the next rebalance |

(The `+risk` rows of the same run belong to [experiment 010](010-shield-allocation-across-agents.md).)

## Setup
US stocks, 20 large caps, 6 default agents, W-MSR consensus (F=1, K=10), 21-day rebalance, 5 bp costs. Limits from [0026](../decisions/0026-safety-thresholds.md) (15% drawdown/252d, 20% vol, 10-day recovery, 20% per stock). Trading 2017-01 to 2025-12. Dev = 2017–2022, test = 2023–2025. Violation = share of days (dd, vol, rec) or rebalances (conc) with robustness < 0. "worst rho_vol" = robustness of phi_vol (-1 = vol at twice the limit).

## Results: flat MAS

Dev (2017–2022)
| Variant | Sharpe | CAGR | Vol | MaxDD | viol dd | viol vol | viol rec | viol conc | worst rho_vol | shield actions | daily cuts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| no shield | 0.714 | 11.7% | 17.7% | -25.9% | 12.4% | 18.9% | 10.7% | 8.3% | -2.50 | 0 | 0 |
| rebalance+uniform | 0.676 | 9.5% | 15.1% | -21.1% | 3.2% | 14.0% | 7.6% | 0% | -1.51 | 37 | 0 |
| **daily+uniform** | 0.656 | 7.8% | 12.8% | **-18.6%** | **1.3%** | **11.2%** | **5.3%** | 0% | **-0.50** | 42 | 197 |

Test (2023–2025), check only
| Variant | Sharpe | CAGR | Vol | MaxDD | viol dd | viol vol | viol rec | worst rho_vol |
|---|---|---|---|---|---|---|---|---|
| no shield | 1.031 | 16.1% | 15.7% | -19.5% | 4.8% | 15.4% | 5.3% | -0.94 |
| rebalance+uniform | 1.086 | 13.4% | 12.3% | -15.9% | 0.4% | 5.1% | 1.6% | -0.29 |
| daily+uniform | 1.151 | 13.9% | 11.9% | -14.9% | 0% | 4.3% | 1.3% | -0.19 |

Stress windows and turnover (full period)
| Variant | Turnover /yr | COVID 2020 ret / maxDD | 2022 ret / maxDD | Apr 2025 ret / maxDD |
|---|---|---|---|---|
| no shield | 5.04 | -16.8% / -21.3% | -8.9% / -15.7% | -3.6% / -11.3% |
| rebalance+uniform | 3.81 | -13.5% / -17.3% | -11.7% / -15.3% | -1.8% / -5.7% |
| daily+uniform | 4.38 | -14.2% / -15.5% | -11.6% / -14.4% | -2.8% / -5.3% |

## Results: hierarchical MAS-H (robustness check)
| Variant | dev Sharpe | dev MaxDD | dev viol vol | dev worst rho_vol | test Sharpe | test viol vol | turnover |
|---|---|---|---|---|---|---|---|
| no shield | 0.755 | -18.6% | 6.7% | -1.34 | 0.918 | 3.2% | 3.54 |
| rebalance+uniform | 0.691 | -18.4% | 6.0% | -1.13 | 0.892 | 2.4% | 3.28 |
| daily+uniform | 0.690 | -16.8% | 3.6% | -0.44 | 0.975 | 0% | 3.70 |

## Findings
1. Daily checks do what they are for: every spec is violated less often and the worst vol breach (COVID) shrinks by two thirds (-1.51 -> -0.50). Same on the hierarchical system, and on the test period.
2. Cost: -0.02 dev Sharpe (noise level), -1.7 pts dev CAGR (it stays de-risked until the next rebalance, so it misses part of rebounds), turnover +15%.
3. The shield (either variant) has a cost in dev Sharpe vs no shield (0.714 -> 0.66–0.68). It is a risk control, not a return enhancer.
4. Neither variant reaches zero vol violations on the flat system: the shield controls ex-ante vol from a 1-year covariance, while phi_vol is measured on 21-day realised vol, which jumps faster than any 1-year estimate.

## Outcome
Adopted: `safety_daily=True` is the default since decision 0028 was accepted. In `run_safety_experiments.py` the variants are now named `no shield`, `rebalance only`, `daily (default)`. A re-run after the change reproduced every number above exactly. Complexity cost is small (two ~12-line blocks) and it is a single flag.

## Follow-ups (not done)
- A short-window or EWMA vol estimate in the shield, to close finding 4. Would be its own decision.
- Allow re-risking within the period (option 3 in 0028) only if the CAGR drag matters.
