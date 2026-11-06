# 0005. ADMM consensus as an alternative mode

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-10-18   Commit: `b48056d`   Where: `consensus.admm_consensus`; `Config.mode="admm"`, `admm_gamma`, `admm_rho`

## Context
The proposal names ADMM as the consensus mechanism.

## Decision
Scaled-form consensus ADMM (lecture slide 73). Agent i's local cost `f_i(x) = -w0_i'x + gamma/2 x'Sigma x` (own view + shared risk term, Sigma scaled to unit average variance). The consensus variable z is the **trust-weighted** average. K iterations per rebalance, then each agent's result is scaled to gross 1. W-MSR stays the default mode.

## Evidence
[Experiment 002](../experiments/002-wmsr-vs-admm.md): ADMM mode turns MAS into a low-vol mean-variance portfolio (vol 6.6%, Sharpe 0.33 vs W-MSR 0.81 on stocks).

## Consequences
This form has a coordinator (z is a global average), so it is "distributed" but not fully decentralised. The fully decentralised edge form was later built for v2 (0021). Its fixed point is the centralised baseline (0027).

## Rollback
`mode="wmsr"` (default).
