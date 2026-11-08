# 0042. Decentralised cell ADMM over a communication graph (dynamic average consensus)

Status: **Accepted (implementation; the topology and resilience experiments come next)**   Date: 2026-11-08   Where: `graph_admm.py`, `engine.py`, `config.py` (`consensus`, `topology`, `gossip_rounds`)   Evidence: tests in `tests/test_graph_admm.py`; experiment 019 (real-data check)

## Context
The proposal ("Resilient Decentralized Portfolio Consensus") promises agents that coordinate over a communication network, and asks how the topology affects convergence. The joint optimiser of [0033](0033-two-level-mas.md) (`cells_admm.solve_cells`) is a sharing ADMM with a HUB: every iteration one node averages all agents' positions, solves the system step (cost of the net trade, gross cap, beta band, priced variance) and sends back one price per coin. Decision 0033 noted that a neighbour-only version needs a gossip step. Three things are global in the hub: the average position, the system step, and the price.

## Options
1. **Keep the hub** and describe it as decentralised. Not what the proposal says; no topology question can be asked.
2. **Dual consensus ADMM** (agents hold local copies of the price and agree on it over edges; Chang, Hong, Wang 2015). Exact, but each agent's step becomes a prox of the sum of two convex conjugates (its own constrained Kelly problem and the system cost), with no closed form here, and positions must be recovered from the dual. Much harder to trace to the lecture notes.
3. **Sharing ADMM with dynamic average consensus** (chosen). Every agent keeps local copies of what the hub held: an estimate s_i of the average position, its own system step z_i and its own price u_i. Per iteration: (a) each agent does its own step against its local price, exactly as in the hub version; (b) each agent adds its change of position to its estimate and the estimates are mixed with the neighbours, `s <- W^r (s + x_new - x_old)`, with W the Metropolis weights of the graph (doubly stochastic) and r gossip rounds; (c) each agent solves the system step from its own estimate (the system data, costs and limits, are public); (d) the prices are updated and mixed the same way, `u <- W^r (u + s_hat - z)`. The sum of the estimates always equals the sum of the positions (W is doubly stochastic), so at a fixed point all estimates equal the true average and all prices agree: the fixed point is the hub's, hence the optimum. On the complete graph with exact mixing it IS the hub algorithm (identical to 1e-15 in the tests).

## Decision
Option 3, in a new module `graph_admm.py`, behind `EngineConfig.consensus = "hub" | "graph"` (default "hub", unchanged behaviour), with `topology` (complete, ring, line, star, random) and `gossip_rounds` (default 1).
- Topology is a mixing matrix only, so experiment 019+ can vary it without touching the agents. The mixing step is also where a resilient (W-MSR-style trimmed) average will go for the resilience experiments.
- Over-relaxation is off by default (1.0) in graph mode: with slow mixing the hub's 1.7 oscillated on an 8-agent ring with one round per iteration; plain ADMM converged.
- Stopping uses, besides the hub's residuals, the disagreement between agents' estimates and between their prices, so a run cannot stop "converged" while agents still disagree (it did before this was added: about 10% off on an 8-agent ring).
- What is still central, and stated as such: the step sizes (rho, sigma) are computed from the mean risk aversion, a number the agents agree on once before trading; the stopping test is evaluated by the simulator (a deployment would use a max-consensus over the graph's diameter).

## Findings before implementation (prototype, random test problems, 3 and 8 agents)
- Complete graph: identical to the hub (difference 1e-15). 3-agent ring and line: same optimum (1e-8).
- 8 agents, all limits binding: with one gossip round per iteration the ring (|lambda_2(W)| = 0.81) needs about 2,700 iterations and the line (0.95) more than 3,000; with 3 rounds the ring needs 400; with 10 rounds the line needs about 600. Slower mixing (larger |lambda_2|) costs more communication: the topology question of the proposal is measurable.
- Two bugs found and fixed while prototyping, recorded because they are easy to reintroduce: mixing BEFORE adding the agent's own change (`s <- W s + dx`) leaves every estimate off by its own last move and the solver failed when the gross cap bound; without mixing the prices, agents can settle on different prices and stop at a wrong point.

## Consequences
- The engine can run either form; results on the real roster (2-3 agents) should be the hub's to solver tolerance on any connected graph. With 2-3 agents most topologies coincide, so the topology experiments need more agents (simulated problems first, as the proposal plans, then variants of the real agents).
- Each agent solves the system step itself: M times the hub's work for that step. Fine at this scale.

## Rollback
Set `consensus = "hub"` (the default). Delete `graph_admm.py` and its tests to remove it.
