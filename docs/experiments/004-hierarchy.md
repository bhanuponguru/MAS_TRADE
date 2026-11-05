# 004. Flat vs hierarchical capital allocation

Date: since `47fa8ee`; numbers re-run   Decision: [0010](../decisions/0010-hierarchy.md)
Command: `uv run python run_backtest.py` (reports MAS and MAS-H)

Numbers re-run on 2026-11-05 (code `92ccc47` + Phase 1 working tree with the shield off, which a test guarantees is identical to the pre-STL code). The original runs were never saved (`results/` is gitignored).

## Variants
| Variant | What it does |
|---|---|
| MAS (flat) | Capital moves between strategies only |
| MAS-H | Also between per-asset subagents inside each strategy; positions = sign(consensus weight) * subagent capital |

## Results (US stocks, 2017–2025)
| | CAGR | Vol | Sharpe | MaxDD | Turnover /yr |
|---|---|---|---|---|---|
| MAS | 13.1% | 17.1% | 0.81 | -25.9% | 5.0 |
| MAS-H | 9.2% | 11.9% | 0.80 | -18.6% | 3.5 |

At the last rebalance the biggest subagent budget in each strategy is only 7–10% (equal share = 5%), so the level-2 reallocation stays close to equal.

## Findings
1. Same Sharpe, lower risk: the hierarchy sizes positions by subagent capital, not by forecast size, which spreads the book (less vol, less drawdown, less turnover).
2. Under attack it is less resilient than flat W-MSR (experiment 003).
3. It stays opt-in. Whether its lower risk is "the hierarchy" or just "smaller positions" has not been separated (a vol-matched flat run would test that).
