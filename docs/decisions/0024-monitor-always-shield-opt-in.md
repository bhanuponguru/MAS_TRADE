# 0024. The STL monitor always runs; the shield is opt-in

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-11-05   Flag: `Config.safety` (default `False`)

## Context
The proposal separates "monitoring safety" from "acting on it". We also need every older result to stay reproducible.

## Decision
`safety.supervise` is called at every rebalance in every run. With `safety=False` it only records the monitor reading (`BacktestResult.safety`: drawdown, ex-ante vol, robustness per spec) and changes nothing. With `safety=True` it also scales the portfolio (see 0025). `run_backtest.py` reports both `MAS` and `MAS+STL`.

A test (`test_shield_off_or_slack_changes_nothing`) checks that a shield with limits that never bind gives exactly the same returns as no shield.

## Rollback
Not needed: the default is the pre-safety behaviour.
