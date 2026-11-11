# 003. Resilience to one compromised agent: plain consensus vs W-MSR

Date: script since `b48056d`, `--hier` since `3e2c17e`; numbers re-run   Decisions: [0002](../decisions/0002-heterogeneous-agents.md), [0004](../decisions/0004-wmsr-consensus-with-pinning.md), [0006](../decisions/0006-capital-flows-through-w.md)
Command: `uv run python run_adversary_experiment.py [--hier]`

Numbers re-run on 2026-11-05 (code `7eff0f1` + Phase 1 working tree with the shield off, which a test guarantees is identical to the pre-STL code). The original runs were never saved (`results/` is gitignored).

## Variants
| Variant | Agents | Consensus |
|---|---|---|
| Clean | 6 default | W-MSR F=1 |
| Attacked, plain | 6 + 1 adversary (all-in on a random stock, random side, frozen in consensus) | F=0 |
| Attacked, W-MSR | 6 + 1 adversary | F=1 |

## Results: flat (US stocks, 2017–2025)
| | CAGR | Vol | Sharpe | MaxDD | Turnover /yr |
|---|---|---|---|---|---|
| Clean | 13.1% | 17.1% | 0.81 | -25.9% | 5.0 |
| Attacked, plain F=0 | 5.7% | 14.4% | **0.46** | -35.5% | 12.4 |
| Attacked, W-MSR F=1 | 10.9% | 15.7% | **0.74** | -27.5% | 7.6 |

## Results: hierarchical
| | CAGR | Vol | Sharpe | MaxDD | Turnover /yr |
|---|---|---|---|---|---|
| Clean | 9.2% | 11.9% | 0.80 | -18.6% | 3.5 |
| Attacked, plain F=0 | 5.6% | 10.7% | 0.56 | -24.4% | 6.9 |
| Attacked, W-MSR F=1 | 6.7% | 10.8% | 0.66 | -21.9% | 5.8 |

Adversary's capital share at the end: 9.8% in every attacked run (it starts at 1/7 = 14.3%).

## Findings
1. One adversary under plain consensus nearly halves the Sharpe (0.81 -> 0.46) and adds 10 points of drawdown. W-MSR F=1 recovers most of it (0.74).
2. The protection comes from **portfolio trimming**, not from capital: the adversary loses the same capital share with and without W-MSR. Trust-driven capital flow is slow (experiment 001).
3. In the hierarchy W-MSR helps less (0.56 -> 0.66 vs clean 0.80).
4. Not tested yet: more than one adversary, F=2, sparse graphs where (F+1,F+1)-robustness fails, smarter adversaries. These are Phase 2 resilience experiments.
