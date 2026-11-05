# 0011. Optional risk- and cost-aware reallocation speed

Status: **Accepted (opt-in)**   Date: 2026-11-01   Commit: `47fa8ee`   Where: `hierarchy.auto_eta`, vector eta in `capital.reallocate_capital`; `Config.eta="auto"`, `eta_sub="auto"`, `risk_aversion`

## Decision
Besides a fixed eta, each agent may get its own speed `eta = a/(a+lam)`, `a = gamma * var * H`, `lam` = cost per typical move. This is the minimiser of "risk of being off target + cost of moving". Riskier agents move faster, costlier trading moves slower. Total capital is still conserved (budget multiplier).

## Evidence
Unit tests only (`tests/test_hierarchy.py`). No performance comparison recorded.

## Rollback
Numeric eta (default 0.5).
