# 0033. Two MAS levels: a wealth-staked market of hypothesis agents, ADMM asset cells

Status: **Accepted (design; mechanisms validated on simulated data, [exp 012](../experiments/012-mas-levels-on-simulated-data.md))**   Date: 2026-11-06   Where: `market.py`, `cells_admm.py`, `agents/base.py` (not yet built)

## Context
A multi-agent system adds nothing over a central optimiser unless agents hold different beliefs, bet different hypotheses, or are coupled by something worth pricing. The earlier ADMM combiner converged to the central solution by construction ([exp 007](../experiments/007-v2-admm-combiner.md)).

## Decision
One principle: **agents that make different bets stake capital; coins inside one agent are coupled by prices.**
- **Level 1, agents = hypotheses (about 7).** Each agent has wealth W_i and a belief mu_ia (its calibrated forecast of net return per coin, from its own model fitted walk-forward on past data and shrunk toward no skill; rule-based agents expose the belief implied by their positions, mu = gamma Sigma x). Each agent stakes Kelly (fraction f_i) on its own belief. The system trades the sum of stakes, netted; each agent's account earns the P&L of its own stake; wealth compounds (floor for survival). No belief-averaging between agents.
- **Level 2, cells = sub-agents (agent i, coin a).** A cell manages one coin inside the agent's capital: capacity, tail risk, cost, execution. All cells are solved jointly by ADMM; the duals are prices of dollar neutrality, factor exposures, margin (capital) and the net trade per coin. Sub-capital is derived from positions, not a separate state.
- Neighbour-only ADMM does not carry over to the sharing form without a gossip step; the baseline is a hub.

## Evidence and limits
Beygelzimer, Langford, Pennock (arXiv 1201.6655): for Kelly bettors the market prediction is a wealth-weighted average of beliefs and wealth follows Bayes' rule (read from the abstract; verify before coding). Evolutionary finance (Blume-Easley; Evstigneev, Hens, Schenk-Hoppe). These are betting-market results: the perps adaptation is ours and is validated on simulated data first (planted skill, over-confidence, decaying skill). With a few strong agents expect wealth to concentrate in carry; five years cannot prove selection speed.

## Findings from simulation (exp 012)
- The cell ADMM matches a one-node reference on every coupling (35 random problems); prices equal the marginal value of the limits.
- Wealth selects skill and drops decayed skill; accounts, cells and wealth add up exactly.
- **A wealth floor blunts selection**: it re-seeds a ruined agent and acts as a rebalancing rule, so an over-confident agent keeps a persistent share (final-wealth ordering against the calibrated agent: 6 of 20 seeds with a 2% floor, 18 of 20 without).
- **An unlimited over-confident agent can ruin the system** (effective Kelly fraction 2: 2-5 of 20 seeds wiped out). Wealth dynamics are too slow to prevent it; the defences are priced margin and gross limits inside the joint problem and the agent calibration spec (which removed ruin entirely).
- Consequence for defaults: no unlimited stakes (margin and gross caps always on), the calibration spec always on, Kelly fractions at or below 0.5, and the floor kept small and justified as a liveness device, not as a selector.

## Consequences
Wealth shifts and belief changes both cause trading; both are priced by the same net cost term inside the joint problem.

## Rollback
Fall back to a fixed-weight (equal-wealth) market: set the wealth update off. The cell ADMM stays.
