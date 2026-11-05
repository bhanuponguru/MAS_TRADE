# 002. Consensus mode: W-MSR vs ADMM

Date: re-run 2026-11-05 (both modes since `b48056d`)   Decisions: [0004](../decisions/0004-wmsr-consensus-with-pinning.md), [0005](../decisions/0005-admm-mode.md)
Command: `uv run python run_backtest.py --mode wmsr` vs `--mode admm`

Numbers re-run on 2026-11-05 (code `92ccc47` + Phase 1 working tree with the shield off, which a test guarantees is identical to the pre-STL code). The original runs were never saved (`results/` is gitignored).

## Variants
| Variant | What it does |
|---|---|
| `mode=wmsr` | K=10 W-MSR rounds with pinning 0.3: agents move toward trusted neighbours but keep 30% of their own view |
| `mode=admm` | K=10 scaled-ADMM iterations: every agent solves own view + shared mean-variance risk term, agrees on a trust-weighted z |

## Results (US stocks, 2017–2025)
| | CAGR | Vol | Sharpe | MaxDD | Turnover /yr |
|---|---|---|---|---|---|
| MAS, W-MSR | 13.1% | 17.1% | 0.81 | -25.9% | 5.0 |
| MAS, ADMM | 2.0% | 6.6% | 0.33 | -12.1% | 8.8 |
| MAS-H, W-MSR | 9.2% | 11.9% | 0.80 | -18.6% | 3.5 |
| MAS-H, ADMM | 5.0% | 6.9% | 0.73 | -10.8% | 5.9 |
| Central MV (one-node optimum of the ADMM problem, added in Phase 1) | 1.4% | 5.9% | 0.27 | -12.2% | 8.9 |

## Findings
1. The two modes solve different problems. ADMM adds a risk term, so its consensus is a mean-variance portfolio: about 1/3 of the vol, much lower return, lower Sharpe, higher turnover.
2. ADMM with K=10 is already close to its centralised optimum (Sharpe 0.33 vs 0.27; turnover 8.8 vs 8.9), consistent with [0027](../decisions/0027-centralised-baseline.md).
3. W-MSR stays the default.
4. `phi_cons` (consensus disagreement) is not comparable across modes: in ADMM mode the logged "disagreement" is the primal residual, not x'Lx.
