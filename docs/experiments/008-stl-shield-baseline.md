# 008. Phase 1: STL monitor, shield and centralised baseline

Date: 2026-11-05 (Phase 1 working tree on `92ccc47`)   Decisions: [0023](../decisions/0023-stl-implementation.md)–[0027](../decisions/0027-centralised-baseline.md)
Command: `uv run python run_backtest.py` (MAS, MAS+STL, Central MV; `results/stl_summary.csv`, `results/stl_robustness.png`)

## Variants
| Variant | What it does |
|---|---|
| MAS | No shield (monitor only) |
| MAS+STL | Shield at every rebalance: per-stock cap 20%, ex-ante vol target 20%, drawdown de-risking (0025) |
| Central MV | One node solving the trust-weighted mean-variance problem (0027) |

## Results (US stocks, 2017–2025, full period)
| | Sharpe | MaxDD | viol dd | viol vol | viol rec | viol conc | worst rho_vol |
|---|---|---|---|---|---|---|---|
| MAS | 0.81 | -25.9% | 13.8% | 17.7% | 8.9% | 15.7% | -2.50 |
| MAS+STL | 0.79 | -21.1% | 5.1% | 11.1% | 5.6% | 0% | -1.51 |
| Central MV | 0.27 | -12.2% | 0% | 0% | 0% | 7.4% | +0.33 |
Shield acted at 62 of 108 rebalances, mean exposure scale 0.79.

## Findings
1. The shield cuts violations roughly in half or better, at almost no Sharpe cost.
2. Breaches that start between rebalances (COVID 2020, April 2025) are not caught, which led to [experiment 009](009-intra-period-safety-checks.md).
3. Scaling all agents alike raised the question of agent-aware cuts, which led to [experiment 010](010-shield-allocation-across-agents.md).

## Update: with the accepted defaults (decisions 0026, 0028, 0029)
Re-run 2026-11-05 after daily checks became the default:
| | Sharpe | MaxDD | viol dd | viol vol | viol rec | viol conc | worst rho_vol | Turnover /yr |
|---|---|---|---|---|---|---|---|---|
| MAS | 0.81 | -25.9% | 13.8% | 17.7% | 8.9% | 15.7% | -2.50 | 5.0 |
| **MAS+STL (daily)** | 0.81 | **-18.6%** | **1.5%** | **8.9%** | **4.0%** | 0% | -0.50 | 4.4 |
The shield acted at 68 of 108 rebalances, mean exposure scale 0.78. Over the full period the shielded system matches the unshielded Sharpe, with 7 points less drawdown and roughly a tenth of the drawdown violations.
