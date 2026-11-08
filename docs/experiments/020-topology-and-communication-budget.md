# 020. Network topology and communication budget of the decentralised optimiser

Date: 2026-11-08   Decision: [0042](../decisions/0042-decentralised-cell-admm-over-a-graph.md)   Code: `graph_admm.py`, `run_topology.py`, `run_benchmark.py`
Proposal question: *How does the communication topology affect convergence and coordination?*

## Question
With agents that only talk to their neighbours (decision 0042), how does the shape of the communication graph change (1) how much communication the agents need to agree on the optimum, (2) how wrong the portfolio is when communication is cut short, and (3) the money made on real data?

## Rules (written and committed before any run)
Measures. For a mixing matrix W (Metropolis weights), the mixing rate |lambda_2(W)| (second largest eigenvalue modulus; consensus error shrinks like |lambda_2|^k) and the algebraic connectivity of the graph (second smallest eigenvalue of the Laplacian, the lecture's measure of how well connected a graph is). Communication = iterations x gossip rounds per iteration x 2 x edges (one message per direction per edge per round).

**Part A, simulated problems** (`run_topology.py`; the random test problems of `tests/test_cells_admm.py` with every limit binding, coupling "all": fee, capacities, margins, gross cap, beta band). Agents M in {4, 8, 16}; topologies complete, ring, line, star, random (Erdos-Renyi p = 0.4, connected); gossip rounds r in {1, 3, 10}; 5 problems (seeds) per cell; tolerance 1e-8, cap 4,000 iterations. The optimum is the hub solver at tolerance 1e-10 (equal to the one-node reference in the tests). The priced volatility term makes each iteration about ten times slower, so it is checked separately at M = 8 (ring and line, r = 3, 3 seeds), not in the grid.
- **A1 (gate):** at r = 3, iterations to converge rise with |lambda_2(W)|: Spearman rank correlation at least 0.7 over (topology, seed) for each M. Non-converged runs enter at the cap.
- **A2 (sanity gate):** the complete graph takes the same number of iterations as the hub at the same relaxation, for every M (it is the hub algorithm).
- **A3 (reported):** for each topology, the gossip rounds r that minimise total messages to converge.
- **A4 (reported):** the error after a fixed budget of K in {25, 50, 100, 200, 400} iterations: net position error max|X_K - X*| / mean|X*|, and the disagreement between agents.

**Part B, real data** (1d, dev period). Eight agents so that topologies differ: carry with 7, 14 and 30-day funding windows; H2 momentum with 15, 30 and 60-day lookbacks; reversal with 3 and 7-day lookbacks. They are parameter variants used to study coordination, not new hypotheses (H2 provisional, reversal not admitted; decisions 0040 and 0041); none of their stand-alone results is used for any decision. Runs: hub; graph complete r = 1; ring r = 1; ring r = 3; line r = 3; star r = 3; and a communication budget: hub and graph ring r = 3 with the solver capped at 200 iterations.
- **B1 (gate):** every uncapped graph run reproduces the hub's net Sharpe within 0.02 and its final equity within 2%.
- **B2 (reported):** rebalances hitting the iteration cap and mean iterations per topology; the capped runs' Sharpe and final equity against the uncapped hub (what limited communication costs).
- **Recommendation rule:** the default topology for the resilience experiments is the configuration with the fewest messages per rebalance that passes B1 with no more capped rebalances than the hub plus 10% of rebalances.

**Amendment 1 (2026-11-08, before any result was seen; the first Part A run was stopped after 46 minutes with no output written).** Each agent solves the system step itself, and with the gross cap and the beta band both binding that step is a nested root search: at M = 16 one iteration took about 0.4 s on the loaded machine, so the 75 sixteen-agent runs (many at the 4,000 cap) would need about 3 hours. The grid is reduced to: M in {4, 8} with the full grid as above; **M = 16 at r = 3 only, 3 seeds** (the setting of gate A1, so A1 is still tested at M = 16). A3 and A4 are reported for M in {4, 8} (and M = 16 at r = 3). Nothing else changes.

Expectation, stated up front: A1 passes (theory: consensus speed is governed by lambda_2); the line is the slowest and the complete graph the fastest; with a short budget the poorly connected graphs leave agents disagreeing and the net position off; on real data B1 passes for the uncapped runs, and the capped runs lose a little because positions are less converged.
