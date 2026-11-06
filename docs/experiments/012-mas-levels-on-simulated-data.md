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
- L2-4 Capital follows its price: with a binding margin, a tighter margin moves capital toward coins with higher edge per unit risk (the best coin's share of the agent's capital rises strictly as the margin tightens).
- L2-5 Purity: the solver depends only on its arguments (no lookahead possible); identical inputs give identical outputs.

**Level 1: market** (simulated coins with planted skill, alpha standard deviation 0.5% per period, idiosyncratic 6%, 60 coins; calibrated belief = rho x signal)
- L1-1 Skilled agent gains share: among a skilled agent (rho = 0.3), a noise agent (rho = 0) and a second skilled agent, the skilled agents' combined wealth share exceeds 0.5 at the horizon T_end = 3 / (difference in expected log-growth between skilled and noise, per period, computed analytically), in at least 90% of 20 seeds.
- L1-2 Over-confidence is punished: a skilled agent whose beliefs are scaled by 4 (Kelly fraction 0.5, so effective fraction 2, where the expected log-growth is zero) has less wealth than the calibrated agent with the same skill at the horizon T_oc (defined in "Changes to criteria") in at least 90% of seeds.
- L1-3 Decay: an agent whose skill drops to zero after T_end periods (while another skilled agent and a noise agent continue) has a lower wealth share at 2 T_end than at T_end, in at least 90% of seeds.
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
(filled in as each criterion is run; run on 2026-11-06 unless stated)

**Level 2, ADMM cells (L2-1 to L2-5): all pass** (42 tests, `tests/test_cells_admm.py`).
- L2-1: 7 coupling configurations x 5 seeds against an SLSQP one-node reference: max |X_admm - X_ref| below 1e-3 of typical |X| and objective gap below 1e-5 in all 35 cases (typical error 1e-7), every constraint satisfied. The hardest case (gross cap and beta band binding together) needs about 1,100 iterations; single couplings need 20-250.
- L2-2: prices are zero when slack and positive when binding; the finite-difference marginal value of the margin and of the gross cap matches the reported price within 5%.
- L2-3: with opposite views on a coin the cost is charged on the net trade and is lower than the separate agents' cost; the joint solution differs from solving apart.
- L2-4: a tighter margin raises the best coin's share of capital strictly.
- L2-5: the solver is a pure function; a warm start reproduces the cold-start solution in no more iterations.
- Engineering finding: the net-position step is a closed form (cost prox with a shifted point for the gross price) and the beta-band price is found by nested bracketed root finding; replacing bisection of the 1-D prox by the closed form made binding system limits 20-40x faster with identical results.

**Level 1, market (L1-1 to L1-4)** (`tests/test_market.py`; f = 0.5, 60 coins, alpha sd 0.5%, idiosyncratic sd 6%, 20 seeds)
- L1-1 passes: skilled agents' combined share exceeds 0.5 at T_end = 160 periods (3 / growth gap 0.0188).
- L1-3 passes: an agent whose skill vanishes after 160 periods has a lower share at 320 than at 160.
- L1-4 passes exactly: account P&Ls sum to the real P&L, cells to the position, wealth to equity, costs to the cost of the net trade, the floor holds (coupled market with fee, impact, capacity, margin, gross cap and beta band).
- L1-2 without a floor passes: the calibrated agent ends with more wealth in 18 of 20 seeds at T_oc = 1,363 (two further seeds are wiped out entirely, see below, and count as failures).
- **L1-2 with a 2% floor FAILS** (strict xfail in the tests): selection against over-confidence is not reliable (the calibrated agent has more final wealth in 6 of 20 seeds; the over-confident agent's mean share is below 0.5 in 14 of the 15 seeds that are not wiped out). See "Changes to criteria" for the diagnosis.
- **Finding: an unlimited over-confident agent can ruin the system.** At an effective Kelly fraction of 2 (belief scaled by 4 at f = 0.5) the per-period return sd is about 0.39, and in 5 of 20 seeds (with floor) the whole system was wiped out in one period. Selection is too slow to stop this; the defence is risk limits (margin and gross cap in the joint problem, tested in L2) and the agent's calibration spec, not wealth dynamics alone.

## Changes to criteria
- 2026-11-06, L2-4: the criterion was first written as the ratio of the best to the worst coin's position. At a tight margin the worst coin's position reaches exactly zero (soft-threshold), making the ratio infinite and the test ill-posed. Replaced by the best coin's share of capital, which states the same thing. Found while writing the test, before any result was read.
- 2026-11-06, L1-2, after a FAILED run (disclosed): with the 2% wealth floor the calibrated agent had more final wealth in only 6 of 20 seeds at T_oc = 1,363 periods. Diagnosis (single-agent run, 6 seeds x 3,000 periods): the calibrated agent's realised log-growth was 0.0141 per period (theory 0.0141), the over-confident one's was -0.0258 (the continuous approximation says 0; discrete compounding makes it negative) with ruin (a period return of -169%) in all 6 runs. So selection works; the floor is what blunts it: it re-seeds a ruined agent with 2% of total wealth and acts as a rebalancing rule, so the over-confident agent keeps a persistent 14-41% mean share and final wealth ordering is close to a coin flip. Two changes follow. (1) Limited liability was added to the market (a loss beyond an account's wealth is borne by the others), which the first version lacked (wealth went negative). (2) L1-2 is split: without a floor, the calibrated agent has more final wealth in at least 90% of seeds; with the 2% floor, the over-confident agent's mean share over the second half is below 0.5 in at least 90% of seeds. The floor's blunting of selection is a finding about decision 0033 and is recorded there.
