# 0008. No lookahead is a tested invariant

Status: **Accepted**   Date: 2026-10-18   Commit: `b48056d`   Where: `tests/test_backtest.py::test_no_lookahead`

## Decision
Everything decided at rebalance t (forecasts, trust, weights, and later the safety shield) may use returns before t only. The test rewrites the future and checks that past decisions do not change. Every new feature adds itself to this test (hierarchy, eligibility, shield, daily checks all did). Walk-forward runs with nothing fitted on the full sample.

## Rollback
None. This is a correctness rule, not a design option.
