# 0010. Two-level hierarchy: per-asset subagents inside each strategy

Status: **Accepted (opt-in)**   Date: 2026-11-01   Commit: `47fa8ee`   Where: `mas_trade/hierarchy.py`; `Config.hierarchical=False`, `eta_sub`, `g_min`, `F_sub`, `sub_graph`

## Context
At level 1, agents only move capital between whole strategies. A second level lets each strategy move capital between the assets it trades, based on which bets pay off.

## Decision
Capital is stored once, as `G[i,k]` = $ run by subagent (strategy i, asset k). Strategy capital = row sum. Per rebalance: the level-1 reallocation on the row sums, then the same `W^T` rule inside each row with subagent trust `s_ik = P(current bet pays) * P(subagent's past P&L positive)`. Position side = sign of the consensus weight. Subagent graph complete, or linked by |correlation| >= 0.3. Frozen adversaries skip level 2. The flat path stays the default.

## Evidence
[Experiment 004](../experiments/004-hierarchy.md): about the same Sharpe as flat (0.80 vs 0.81), with lower vol (11.9% vs 17.1%), drawdown (-18.6% vs -25.9%) and turnover. Under attack, W-MSR helps less than in the flat system.

## Rollback
`hierarchical=False`.
