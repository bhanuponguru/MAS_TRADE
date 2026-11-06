# 0036. Factor risk model, priced limits inside the ADMM, STL placements

Status: **Accepted (design; STL specs and priced limits validated on simulated data, [exp 012](../experiments/012-mas-levels-on-simulated-data.md))**   Date: 2026-11-06   Where: `risk.py`, `stl.py`, `cells_admm.py` (not yet built)

## Context
The v1 shield scaled the finished portfolio toward cash after the fact ([0025](0025-shield-mechanism.md)); rescaling a cost-aware solution re-trades the whole book (seen in exp 007). Its limits were justified by a risk mandate ([0026](0026-safety-thresholds.md)), which is the part worth keeping.

## Decision
- Risk model for cells: Sigma = B F B' + D (BTC beta plus one or two PCA factors; Ledoit-Wolf for F), so risk is separable per coin plus a few factor exposures, each with a price.
- System limits (vol, drawdown, gross, BTC-beta band, concentration, margin) are constraints inside the ADMM with dual prices, not post-hoc scaling.
- STL placements: inputs (belief sanity, feature freshness), cell (capacity, loss-and-recover), execution (deadline), agent (rolling contribution, drawdown, calibration, opportunity scaling its Kelly fraction by the margin), system (priced limits), market (wealth-share cap), reporting (robustness traces).
- Every limit needs a mandate argument recorded before any run, as in 0026; limits are never chosen by comparing Sharpe. Values for the old shield (0026) are superseded.

## Consequences
More specs mean more tunables; each is justified up front and logged.

## Rollback
Constraints can be loosened per spec; there is no post-hoc shield to fall back on.
