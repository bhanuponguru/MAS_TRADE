# 017. Residual reversal as the third agent, and the market of three (Phase 4)

Date: 2026-11-07   Decision: [0040](../decisions/0040-reversal-agent-and-admission-gate.md)   Code: `agents/reversal.py`, `compare_reversal.py`
Commands: `uv run python run_benchmark.py --bar B --agents RankReversal --label "017 reversal alone" --tag B_broad_RankReversal --boot 500` and `--agents RankCarry TSMomentum RankReversal --label "017 market of three" --tag B_broad_RankCarry+TSMomentum+RankReversal` for B in 1d, 4h, 1h, then `uv run python compare_reversal.py`.

## Question
Is residual reversal an admissible third agent, and does a market of three agents beat both the market of two and a fixed blend of the stand-alone runs?

## Rules (fixed before any run of the agent)
As decision 0040. In short: admission needs (a) stand-alone net Sharpe lower bound above 0, (b) rank IC t > 2, (c) alpha above 0 against BTC, carry and H2 stand-alone returns, each on at least two of three bar sizes; market acceptance against the market of two by the ladder rule; the market against the inverse-volatility blend and the cost comparison are reported. Carry alone, H2 alone and carry + H2 are the 015b runs (same engine; reproduced).

**Expectation, stated up front.** The legacy reversal lost after costs, so the likely result is that reversal fails (a) on 1d at least; the IC is real but short-lived (IC at twice the holding period falls to 0.003 on 1d) while the engine's 1d rebalance is 14 days. On 1h and 4h the IC is more persistent. The market of three is more informative about the structure than about reversal.
