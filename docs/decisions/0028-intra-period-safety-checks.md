# 0028. Shield checks every bar between rebalances (de-risk only)

Status: **Accepted** (2026-11-05, approved by the user on the experiment's recommendation)   Date: 2026-11-05   Flag: `Config.safety_daily` (default **`True`** since acceptance; only matters when `safety=True`)

## Context
With the shield acting only at rebalances (every 21 days), a crash that starts mid-period runs unchecked: COVID 2020 and April 2025 still breached the vol and drawdown specs.

## Options
1. **Rebalance only** (current default).
2. **Daily check, de-risk only**: every bar, run the same `supervise` on data before that bar; if it asks for less exposure than currently held, cut to that level (pay costs on the trade). Never add exposure back until the next rebalance, so it cannot whipsaw. About 25 extra lines in `backtest.py` (both paths).
3. Daily check that can also re-risk: faster recovery, more turnover and whipsaw. Not tried.

## Decision
Option 2, based on [experiment 009](../experiments/009-intra-period-safety-checks.md) (dev period): fewer violations on every spec, worst vol breach -1.51 -> -0.50, max drawdown -21.1% -> -18.6%, at a cost of -0.02 Sharpe and +15% turnover. The test period agrees (Sharpe 1.09 -> 1.15).

## Consequences
More trades (turnover 3.8 -> 4.4 per year). After a cut, the system stays de-risked until the next rebalance, which lowers CAGR in recoveries.

## Rollback
`Config.safety_daily=False` (the rebalance-only shield; still tested). Removing the code: delete the `if daily and d > t:` blocks in both paths of `run_backtest`.
