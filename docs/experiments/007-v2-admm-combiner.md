# 007. v2 decentralised ADMM combiner with true costs

Date: 2026-11-05 (`7eff0f1`)   Decision: [0021](../decisions/0021-v2-decentralised-admm.md)
Command: `uv run python run_v2_benchmark.py --bar ...` (ADMM rows, plus `admm_convergence.csv`)

## Status
Finding copied from the commit message. Tables not saved; crypto data not on this machine.

## Question
If the agents' consensus objective contains the executor's real trading cost (fee + sqrt impact), does the agreed portfolio trade less and lose less to costs?

## Finding (dev period)
Putting the true cost in the objective **did not lower cost drag**.

## Verified by tests
The decentralised result matches the one-node optimum (`central_solve`), neutrality holds locally, higher costs never mean more trading, Hedge weighting works, and there is no lookahead.
