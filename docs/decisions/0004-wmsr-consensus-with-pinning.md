# 0004. Consensus: trust-weighted W-MSR with pinning

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-10-18   Commit: `b48056d`   Where: `consensus.trust_matrix`, `run_consensus`; `Config.K=10, F=1, pin=0.3, graph`

## Context
Agents must move toward a shared allocation over a communication graph, and some agents may be faulty or malicious.

## Decision
- Consensus matrix `W_ij = a_ij s_j / sum_l a_il s_l` (row-stochastic: listen more to trusted neighbours).
- K=10 rounds of **W-MSR** per rebalance (per stock, drop the F largest and F smallest neighbour values relative to your own). F=1 by default; F=0 is plain consensus.
- **Pinning** (leader-follower): `x <- (1-b) WMSR(x) + b w0` with b=0.3, so agents keep part of their own view and the result is not one identical portfolio.
- Default graph complete; Erdos-Renyi (`graph="er"`) as an option. Adversarial agents are frozen: they keep broadcasting their own portfolio.

## Rationale (documented)
Taken from the course notes (consensus theory, W-MSR resilient consensus, leader-follower pinning). (F+1, F+1)-robust graphs tolerate F adversaries; `is_r_s_robust` checks this for small graphs.

## Evidence
[Experiment 003](../experiments/003-adversary-resilience.md): W-MSR F=1 keeps most of the clean system's Sharpe under attack, plain consensus does not.

## Rollback
`F=0` (plain), `pin=0` (full consensus).
