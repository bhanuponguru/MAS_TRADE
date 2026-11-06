# 0032. Replace v1 and v2 with one new implementation

Status: **Accepted**   Date: 2026-11-06   Where: whole repository (branch `engine-rebuild`)

## Context
The repository held two engines: v1 (consensus MAS: W-MSR, trust, capital flow, hierarchy, safety shield) and v2 (neutral books, combiners, consensus-ADMM). Evidence from them ([exp 001-010](../experiments/)):
- Only funding carry has a net edge; no combiner beats inverse-vol; the consensus layer added turnover without return.
- The combination layer was not the bottleneck: the agents carried too little information.
- The "MAS" was a distributed solver for one problem that a central optimiser solves identically.

## Options
1. Keep both and add a third engine beside them. Accumulates code nobody will run.
2. Freeze v2 and build on v1 (decision 0022).
3. **Replace** both with one implementation built around hypothesis agents, a wealth-staked market and ADMM cells ([0033](0033-two-level-mas.md)).

## Decision
Option 3. Superseded code is deleted, not preserved. History is kept only as:
- the experiments and decision records (this folder and `../experiments/`), statuses changed to Superseded;
- git tag `legacy-v1-v2` (commit `cf16351`): reproducing an old result means checking out that tag in a separate worktree;
- small reference tables in `../experiments/data/` (dev-period only; the sealed-holdout tables were not copied).
README describes only the new system.

Kept and moved: the Binance data pipeline (`data.py`), panel, cost model, Ledoit-Wolf and betas (`risk.py`), diagnostics (IC, regimes, deflated Sharpe, trial log), metrics, the cost prox (`cells_admm.py`) and the STL operators (`stl.py`, the contributor's module with the v1 shield removed).

## Consequences
- The stock demo, W-MSR consensus, trust-weighted capital flow, hierarchy, adversary experiment and the v1 shield exist only at the tag. The contributor's safety-layer work is reduced to its STL operators; the specs are rebuilt on the new structure ([0036](0036-risk-model-and-stl-placement.md)).
- Scope is crypto perpetuals. The yfinance dependency is removed.

## Rollback
`git switch -c legacy legacy-v1-v2`. Nothing else is needed; the new work is on its own branch until merged.
