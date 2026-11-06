# 0017. v2 combiners: compare several ways to mix agent books

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-11-01   Commit: `47fa8ee`   Where: `v2/combiners.py`

## Decision
Implement and compare: EW, inverse-vol, Fixed-Share Hedge (online learning with regime switching), risk budgeting, Hedge + risk budgeting, and C3 IC-calibrated view fusion (correlation-aware regression of returns on scores, then a mean-variance book).

## Evidence
[Experiment 006](../experiments/006-v2-dev-findings.md): none beat inverse-vol on the dev period.
