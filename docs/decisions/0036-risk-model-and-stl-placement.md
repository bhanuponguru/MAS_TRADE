# 0036. Factor risk model, priced limits inside the ADMM, STL placements

Status: **Accepted (design; STL specs and priced limits validated on simulated data, [exp 012](../experiments/012-mas-levels-on-simulated-data.md))**   Date: 2026-11-06   Where: `risk.py`, `stl.py`, `cells_admm.py` (not yet built)

## Context
The v1 shield scaled the finished portfolio toward cash after the fact ([0025](0025-shield-mechanism.md)); rescaling a cost-aware solution re-trades the whole book (seen in exp 007). Its limits were justified by a risk mandate ([0026](0026-safety-thresholds.md)), which is the part worth keeping.

## Decision
- Risk model for cells: Sigma = B F B' + D (BTC beta plus one or two PCA factors; Ledoit-Wolf for F), so risk is separable per coin plus a few factor exposures, each with a price.
- System limits (vol, drawdown, gross, BTC-beta band, concentration, margin) are constraints inside the ADMM with dual prices, not post-hoc scaling.
- STL placements: inputs (belief sanity, feature freshness), cell (capacity, loss-and-recover), execution (deadline), agent (rolling contribution, drawdown, calibration, opportunity scaling its Kelly fraction by the margin), system (priced limits), market (wealth-share cap), reporting (robustness traces).
- Every limit needs a mandate argument recorded before any run, as in 0026; limits are never chosen by comparing Sharpe. Values for the old shield (0026) are superseded.

## Amendments (2026-11-07, experiments 012 and 015)
- The system volatility limit is implemented as a PRICE on the system variance: a term (vol_penalty / 2) X'(D + B F B')X in the joint problem, with a multiplier searched until ex-ante volatility is 20%. At equal total volatility the priced limit left a neutral agent 97% of its unconstrained book where a uniform shrink of every stake left it 45%, and the price fell on the factor exposure. The beta band is a priced constraint (system net beta within +-0.25 of equity).
- The calibration spec acts on the upper confidence bound of the slope, because a card-sized belief has a slope standard error above 1 over 3,000 observations; the sanity spec tests the volatility-standardised belief. Both were found by wiring them into the real-data engine.
- Solver notes: relative stopping rule (1e-6), over-relaxation 1.7, penalty 5x; the net position is accurate to about 1e-6, the split between agents less so.

## Amendment (2026-11-08, bug fix): the volatility limit is a share of current equity
The ex-ante volatility of the system was compared with `target_vol` in units of the INITIAL equity, while cell positions are in those units and Kelly stakes grow with wealth; the gross cap and beta band were already scaled by current equity. The effective limit was therefore 20% / (equity multiple): about 7-8% of equity by 2025 on the daily carry + momentum run. The engine now uses `target_vol x current equity`. This restores the decision as written, it is not a new limit; results of experiments 013-017 were computed before the fix. Rollback: commit 1febff1.

## Consequences
More specs mean more tunables; each is justified up front and logged.

## Rollback
Constraints can be loosened per spec; there is no post-hoc shield to fall back on.
