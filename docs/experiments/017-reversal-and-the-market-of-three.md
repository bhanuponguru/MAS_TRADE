# 017. Residual reversal as the third agent, and the market of three (Phase 4)

Date: 2026-11-07   Decision: [0040](../decisions/0040-reversal-agent-and-admission-gate.md)   Code: `agents/reversal.py`, `compare_reversal.py`
Commands: `uv run python run_benchmark.py --bar B --agents RankReversal --label "017 reversal alone" --tag B_broad_RankReversal --boot 500` and `--agents RankCarry TSMomentum RankReversal --label "017 market of three" --tag B_broad_RankCarry+TSMomentum+RankReversal` for B in 1d, 4h, 1h, then `uv run python compare_reversal.py`.

## Question
Is residual reversal an admissible third agent, and does a market of three agents beat both the market of two and a fixed blend of the stand-alone runs?

## Rules (fixed before any run of the agent)
As decision 0040. In short: admission needs (a) stand-alone net Sharpe lower bound above 0, (b) rank IC t > 2, (c) alpha above 0 against BTC, carry and H2 stand-alone returns, each on at least two of three bar sizes; market acceptance against the market of two by the ladder rule; the market against the inverse-volatility blend and the cost comparison are reported. Carry alone, H2 alone and carry + H2 are the 015b runs (same engine; reproduced).

**Expectation, stated up front.** The legacy reversal lost after costs, so the likely result is that reversal fails (a) on 1d at least; the IC is real but short-lived (IC at twice the holding period falls to 0.003 on 1d) while the engine's 1d rebalance is 14 days. On 1h and 4h the IC is more persistent. The market of three is more informative about the structure than about reversal.

## Status when work was stopped (2026-11-08): INCOMPLETE, no verdict on the market yet
Done: reversal alone on 1d, 4h, 1h; market of three on 1d and 4h. **Missing: the market of three on 1h**, so market acceptance, gate (c) and the blend comparison are not decided here. The runs of reversal alone were executed twice (a reboot erased the first logs); the repeat reproduced every number, and the trial log therefore holds each of them twice (count once for the deflated Sharpe). Logs: `results/<bar>_broad_RankReversal/run.log`.

**Reversal alone (the stand-alone gates, from the run logs):**
| Bar | Net Sharpe (90% interval) | CAGR | Vol | Max drawdown | Rank IC (t) | Turnover | Annual cost | IC by liquidity tercile (0 = least liquid) |
|---|---|---|---|---|---|---|---|---|
| 1d | -0.57 (-1.18 to +0.05) | -30.2% | 44.9% | -87.4% | 0.025 (1.5) | 30.8 | -9.7% | 0.037 / 0.048 / -0.024 |
| 4h | -1.08 (-1.68 to -0.44) | -45.2% | 45.9% | -96.7% | 0.041 (4.3) | 39.7 | -15.5% | 0.031 / 0.057 / 0.031 |
| 1h | -0.83 (-1.45 to -0.19) | -37.6% | 44.7% | -93.2% | 0.046 (7.3) | 58.1 | -17.3% | 0.051 / 0.064 / 0.030 |

By the rules above: gate (a) FAILS (Sharpe lower bound below 0 on all three bars); gate (b) passes (IC t above 2 on 4h and 1h); so **reversal is not admitted** whatever gate (c) shows. The skill is real but the stand-alone book loses to costs on every bar, as the legacy implementation did. Realised volatility (about 45%) is more than twice the 20% ex-ante limit, the known weakness of the one-factor risk model for imperfectly neutral books, so these drawdowns are at an oversized scale. The IC is highest in the middle liquidity tercile on every bar, so the card's "stronger in less liquid coins" mechanism is not supported.
