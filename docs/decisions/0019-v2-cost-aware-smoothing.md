# 0019. v2 cost-aware partial adjustment (opt-in)

Status: **Superseded by 0032** (was: Accepted (opt-in))   Date: 2026-11-01   Commit: `47fa8ee`   Where: `v2/smooth.py`; `--smooth`

## Decision
Each book trades only part of the way to its target, `w = p + eta (tau - p)`, `eta = a/(a+lam)` (Garleanu-Pedersen style, the same form as 0011). Neutral books keep their neutrality, and the timing book is not projected.

## Rollback
Leave out `--smooth`.
