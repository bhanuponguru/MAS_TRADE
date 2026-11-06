# 0006. Agents own capital; it moves through W transpose

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-10-18   Commit: `b48056d`   Where: `capital.reallocate_capital`; `Config.eta=0.5, c_min=0.02, F_capital=0`

## Context
Consensus on portfolios alone does not reward good agents. Capital allocation is the second channel.

## Decision
Each agent controls its own dollars `c_i`. At each rebalance `c <- (1-eta) c + eta W^T c`. W is row-stochastic, so total capital is conserved (asserted). On a complete graph it drifts toward trust. A floor `c_min` (2% of total) keeps every agent alive. W-MSR trimming on the trust values for this step is a separate knob `F_capital` (default 0).

## Rationale (documented)
Same conservation argument as `1'L = 0` in the consensus notes: capital is a quantity that flows, never created.

## Evidence
[Experiment 001](../experiments/001-stock-baseline.md): over 2017–2025 capital shares barely move (each stays 14–20%). [Experiment 003](../experiments/003-adversary-resilience.md): the adversary's share falls from 14.3% to 9.8%.

## Rollback
`eta=0` freezes capital at equal shares.
