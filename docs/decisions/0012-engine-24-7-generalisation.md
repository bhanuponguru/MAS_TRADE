# 0012. Generalise the engine to 24/7 perpetual futures

Status: **Accepted**   Date: 2026-11-01   Commit: `47fa8ee`   Where: `run_backtest(..., eligible, funding)`, `Config.periods_per_year`, `Config.for_tier`, `default_agents(scale)`

## Context
Stocks give one market and a survivorship-biased universe (0001). Crypto perps trade 24/7 with listings, delistings and funding payments.

## Decision
- NaN return = not trading. An asset is tradable at t only if `eligible[t]` (point-in-time) and its whole lookback window is valid. Ineligible assets get zero weight and zero subagent budget.
- `funding` is charged to longs and paid to shorts (P&L uses `R - funding`, forecasts use price returns).
- All schedule fields are in **bars**. `periods_per_year` annualises. `Config.for_tier(bar)` converts time units to bars for 1d/4h/1h/15m/5m. `default_agents(scale=lookback/252)` keeps agent windows proportional.
- Listings start trading only after warmup. A universe collapse after trading starts is an error, not silent.

## Rollback
Stock runs are unchanged (no eligibility or funding passed).
