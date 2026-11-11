# 0018. v2 costs: fee + square-root impact, and a liquidity floor

Status: **Accepted**   Date: 2026-11-01   Commit: `3e2c17e`   Where: `v2/costs.py`; `V2Config.fee_bps=5, impact_k=1, aum, min_adv=1e6`

## Decision
Cost per trade = `|d| * (fee + k * daily_vol * sqrt(|d| * AUM / ADV))`. An asset is tradable only if its trailing median daily dollar volume >= `min_adv` ($1M).

## Rationale (documented)
Zero-volume assets once produced 300% impact costs. A flat bp cost understates slippage in illiquid names (0013).

## Rollback
`min_adv=0`, `impact_k=0`.
