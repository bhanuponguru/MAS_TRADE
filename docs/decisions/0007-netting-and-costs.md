# 0007. Execution: system position nets agents' trades; costs on the net trade

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-10-18   Commit: `b48056d`   Where: `backtest.run_backtest`; `Config.cost_bps=5, rebalance_days=21, lookback=252, warmup=252`

## Decision
System position `h = sum_i c_i x_i`, so opposite trades by different agents cancel, and costs (5 bp per $ traded) are charged on `|h_new - h_old|` only. Rebalance every 21 trading days with a 252-day lookback and a 252-day warmup of standalone track records before trading. Baselines in every run: each agent alone, the naive average of agent portfolios, equal-weight long-only, and the benchmark.

## Rationale (inferred)
That is how one fund running several strategies would trade. Charging each agent separately would overstate costs.

## Rollback
Config fields.
