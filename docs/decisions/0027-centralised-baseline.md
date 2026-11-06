# 0027. Centralised baseline = the optimum of the ADMM problem

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-11-05   Where: `consensus.central_mv`, column "Central MV"

## Context
The proposal promises a centralised portfolio optimiser as a reference for the distributed system.

## Options
1. **Same problem, one node**: minimise `sum_i s_i f_i(x)` with ADMM's local costs `f_i(x) = -w0_i'x + gamma/2 x'Sigma x`. Closed form `x* = (gamma Sigma)^-1 (trust-weighted average of agent portfolios)`.
2. A textbook Markowitz portfolio on sample means: a different problem, so differences would mix "distributed vs central" with "different objective".

## Decision
Option 1. It is exactly ADMM's fixed point (tested: `test_admm_converges_to_central_optimum`), so it is both the baseline and the convergence target (distance to it measures how far K ADMM rounds are from the optimum).

## Consequences
On stocks it is a very low-risk portfolio (vol 6%, Sharpe 0.27): gross exposure 1 split long/short by a mean-variance solve. That is a property of the reference problem, not a bug.

## Rollback
Remove the column; nothing else depends on it.
