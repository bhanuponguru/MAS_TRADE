# 012. Both MAS levels on simulated data (Phase 1)

Date: 2026-11-06   Decisions: [0033](../decisions/0033-two-level-mas.md), [0035](../decisions/0035-drop-wmsr-and-belief-averaging.md), [0036](../decisions/0036-risk-model-and-stl-placement.md)
Code: `mas_trade/cells_admm.py`, `market.py`, `agents/averaging.py`, `simulate.py`, `stl.py`; tests in `tests/`.

## Why simulated data
The mechanisms (prices, wealth selection, netting, fusion, timing) must be validated where the truth is known, independent of the noisy crypto data. Nothing here is tuned: the criteria below were written before the code and are applied as written. Any change to a criterion after seeing a result is recorded in "Changes to criteria" with the reason.

## Pass criteria (fixed before implementation)
**Level 2: ADMM cells** (random problems, 3-4 agents, 6-10 coins, 5 seeds each, every coupling on its own and all together: net cost with fee, capacity box, margin, gross cap, BTC-beta band)
- L2-1 Optimality: against a one-node reference solve of the same problem, max |X_admm - X_ref| <= 1e-3 x (typical |X|) and relative objective gap <= 1e-5, with the ADMM stopped by its own residual rule (not an oracle).
- L2-2 Prices: every price is >= 0 and exactly 0 when its constraint is slack; for the margin price and the gross-cap price, the finite-difference change of the optimal objective per unit of the limit equals minus the price within 5%.
- L2-3 Netting: for two agents with opposite views on a coin, the cost charged equals the cost of the NET trade; it is strictly below the sum of the two agents' separate costs, and the solution differs from solving the agents separately.
- L2-4 Capital follows its price: with a binding margin, a tighter margin moves capital toward coins with higher edge per unit risk (the ratio of the positions of the best and worst coin rises).
- L2-5 Purity: the solver depends only on its arguments (no lookahead possible); identical inputs give identical outputs.

**Level 1: market** (simulated coins with planted skill, alpha standard deviation 0.5% per period, idiosyncratic 6%, 60 coins; calibrated belief = rho x signal)
- L1-1 Skilled agent gains share: among a skilled agent (rho = 0.3), a noise agent (rho = 0) and a second skilled agent, the skilled agents' combined wealth share exceeds 0.5 at the horizon T_end = 3 / (difference in expected log-growth between skilled and noise, per period, computed analytically), in at least 90% of 20 seeds.
- L1-2 Over-confidence is punished: a skilled agent whose beliefs are scaled by 4 has less wealth than the calibrated agent with the same skill at T_end in at least 90% of seeds.
- L1-3 Decay: when an agent's skill drops to zero halfway, its wealth share falls within 2 x the time it took to build, in at least 90% of seeds.
- L1-4 Accounting (exact, 1e-9): the sum of the agents' account P&Ls equals the real P&L; the cells sum to the real system position; the wealths sum to real equity; the wealth floor keeps every share >= the floor.

**Model averaging**
- A1 Error-weighted averaging has lower forecast error than equal weighting when member error variances differ by a factor of 4 or more, and is not worse than equal weighting by more than 2% when they are equal (20 seeds).
- A2 An injected exploding member (x100) changes the fused belief by less than 10% with the trimmed mean / sanity guard on, and the effect is reported when off.

**STL**
- S1 The recovery spec flags only breaches longer than R bars and the deadline spec flags a target not reached within N bars (both against brute force).
- S2 The belief-sanity spec zeroes an injected corrupt belief (NaN or 100x) and leaves honest ones untouched; the spec margin scales an agent's Kelly fraction monotonically.

**Timing**
- T1 With planted regime-dependent skill (rho 0.3 in the "on" state, 0 in "off"; the state variable observable), the timed agent earns more than its untimed twin (paired mean difference > 0, 90% bootstrap interval above 0) over 20 seeds pooled.
- T2 With no dependence, the timed agent is not worse than the untimed twin by more than the shrinkage cost: mean difference >= -10% of the untimed agent's mean return.

## Results
(to be filled in as each criterion is run)

## Changes to criteria
None yet.
