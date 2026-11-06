# 0031. Crypto drawdown limit consistent with the crypto vol limit

Status: **Superseded by 0032** (was: Proposed) (not applied; needs team sign-off)   Date: 2026-11-05   Flag: `Config.for_tier(..., safety_max_dd=...)`

## Context
[0026](0026-safety-thresholds.md) set crypto's vol limit to 40% but left the drawdown limit at the stocks' 15%. For stocks the two limits are in proportion (15% drawdown / 20% vol = 0.75). For crypto they are not (15% / 40% < 0.4): a portfolio running exactly at its vol limit would breach the drawdown limit in an ordinary bad month. [Experiment 005](../experiments/005-v1-crypto-benchmark.md) shows the result: the drawdown spec is violated on about 60% of bars even with the shield, which then keeps exposure near its 20% floor.

## Options
1. **Same ratio as stocks**: `safety_max_dd = 0.75 * 0.40 = 30%` over 365 days. Follows from the existing mandate, not from performance.
2. Keep 15% and lower the crypto vol limit to 20% (same as stocks): a much smaller crypto book.
3. Keep both as they are and accept a mostly de-risked shield.

## Proposal
Option 1, because it follows from a rule already accepted for stocks. It must be chosen on this argument, not by comparing dev-period Sharpe across values, and **must not be evaluated on the crypto holdout**.

## Rollback
One field in `Config.for_tier`.
