# 0021. v2: decentralised consensus-ADMM combiner on a ring

Status: **Accepted**   Date: 2026-11-05   Commit: `92ccc47`   Where: `v2/admm.py`, `combiners.admm_consensus`; `V2Config.admm_*`

## Context
The v1 ADMM (0005) has a global average step. The proposal is about decentralised agents.

## Decision
Edge-form consensus ADMM (Shi et al. 2014, lecture slide 76) over a ring of agents (neighbours only). Agent i's local objective: its IC-calibrated view, weighted by its Fixed-Share Hedge budget, plus a shared risk term and the executor's **true** trading cost (fee + impact) of the net trade, under local neutrality. `central_solve` is the one-node reference.

## Evidence
[Experiment 007](../experiments/007-v2-admm-combiner.md): documented result: putting the true cost in the objective did not lower cost drag.

## Rollback
Drop the ADMM rows from `run_v2_benchmark.py`.
