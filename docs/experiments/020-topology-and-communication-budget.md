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

## Results, part A (simulated problems)
Command: `uv run python -u run_topology.py --workers 4` (about 3 hours on the shared machine). Tables: [partA_runs.csv](data/020/partA_runs.csv) (one row per run), [partA_summary.csv](data/020/partA_summary.csv) (medians per cell), [partA_budget.csv](data/020/partA_budget.csv) (error after K iterations), [partA_vol.csv](data/020/partA_vol.csv) (priced-volatility check).

**A1 (gate): FAIL.** Spearman correlation of |lambda_2(W)| with iterations at r = 3: **0.599 at M = 4** (rule: at least 0.7), 0.897 at M = 8, 0.783 at M = 16. The rule required all three.

Why it fails at M = 4 (diagnosis after the verdict; it does not change it). At four agents the graphs are all small and differ little, and the difficulty of the problem itself dominates: seed 0 takes 828-830 iterations on EVERY topology, including the complete graph, because the ADMM itself is slow on that problem, not the consensus. Pooling seeds therefore mixes problem difficulty with topology. Inside each problem the ordering is as theory says (mean within-seed Spearman 0.785 at M = 4, 0.960 at M = 8, 0.816 at M = 16), but that is not the pre-registered statistic.

Median iterations to converge at r = 3 (5 problems; 3 at M = 16; cap 4,000); in brackets the mixing rate |lambda_2(W)| of each topology, in column order:

| M | complete | ring | random | star | line |
|---|---|---|---|---|---|
| 4 (mixing rate: 0 / 0.33 / 0.75 / 0.75 / 0.80) | 151 | 165 | 228 | 264 | 389 |
| 8 (0 / 0.80 / 0.68 / 0.88 / 0.95) | 386 | 499 | 883 | 1,183 | 4,000 (none converged) |
| 16 (0 / 0.95 / 0.79 / 0.94 / 0.99) | 1,000 | 3,709 (2 of 3 converged) | 1,000 | 4,000 (none) | 4,000 (none) |

**A2 (sanity gate): PASS.** The complete graph takes exactly the hub's number of iterations in every case (it is the hub algorithm).

**A3 (reported): gossip rounds that minimise total messages.** One round is cheapest on the complete graph (more rounds change nothing there) and, at M = 4, on the ring. Everywhere else three rounds are cheapest: one round needs so many more iterations (or does not converge in 4,000) that the extra messages per iteration pay for themselves, and ten rounds waste messages once mixing is no longer the bottleneck. Median messages at M = 8: complete 21,616 (r = 1), ring 23,952, star 49,686, random 52,980 (all r = 3); the line does not converge at r = 1 or 3 and needs 91,840 at r = 10.

**A4 (reported): error after a fixed budget.** At r = 3 the net-position error after K iterations is almost the same on every topology (M = 8: about 0.40 at K = 25, 0.16 at K = 100, 0.03-0.05 at K = 200, below 0.001 at K = 400; M = 16: 0.76 at K = 100, 0.16 at K = 200, about 0.012-0.015 at K = 400). The early iterations are limited by the ADMM itself, not by the communication; topology decides how long the last, precise part takes (the tolerance 1e-8 and the agents' agreement on prices).

**Priced-volatility check (M = 8, r = 3).** The ring converges in 797-1,076 iterations (hub: 165-749); the line hits the 4,000 cap on all three problems, but with net-position error at most 4.3e-6 of a typical position.

## Results, part B (real data, 1d, dev period, eight agents)
Commands (the eight runs were started in parallel):
```
AG="RankCarry:7 RankCarry:14 RankCarry:30 TSMomentum:15 TSMomentum:30 TSMomentum:60 RankReversal:3 RankReversal:7"
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 020_eight_hub
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 020_eight_<topology>_r<R> --consensus graph --topology <topology> --rounds <R>
    # (complete, 1), (ring, 1), (ring, 3), (line, 3), (star, 3)
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --iters 200 --tag 020_eight_hub_cap200
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --iters 200 --tag 020_eight_ring_r3_cap200 --consensus graph --topology ring --rounds 3
``` Table: [data/020/partB_runs.csv](data/020/partB_runs.csv). 135 rebalances; engine iteration cap 3,000 unless stated. Messages per rebalance = mean iterations x rounds x 2 x edges (complete 28 edges, ring 8, line and star 7); the mean counts only the last solve of each rebalance (the volatility search may solve more than once).

| Run | Net Sharpe | CAGR | Final equity (vs hub) | Rebalances at the iteration cap | Mean iterations | Messages per rebalance |
|---|---|---|---|---|---|---|
| hub | 1.240 | 26.0% | 3.578 | 27 | 1,427 | (hub) |
| graph complete, 1 round | 1.239 | 26.0% | 3.577 (-0.02%) | 29 | 1,459 | 81,716 |
| graph ring, 1 round | 1.238 | 26.0% | 3.572 (-0.16%) | 114 | 2,885 | 46,160 |
| graph ring, 3 rounds | 1.239 | 26.0% | 3.575 (-0.08%) | 43 | 1,870 | 89,755 |
| graph line, 3 rounds | 1.238 | 25.9% | 3.570 (-0.22%) | 122 | 2,949 | 123,854 |
| graph star, 3 rounds | 1.240 | 26.0% | 3.578 (-0.01%) | 96 | 2,743 | 115,194 |
| hub, 200 iterations | 1.217 | 25.3% | 3.478 (-2.81%) | 135 | 200 | (hub) |
| graph ring 3 rounds, 200 iterations | 1.212 | 25.2% | 3.453 (-3.51%) | 135 | 200 | 9,600 |

Volatility 20.2-20.3% and maximum drawdown -29.8% to -30.0% in every run.

**B1: PASS.** Every uncapped graph run is within 0.002 Sharpe of the hub (rule: 0.02) and within 0.23% of its final equity (rule: 2%).

**B2 (reported).** Sparser graphs hit the iteration cap far more often: 29 of 135 rebalances on the complete graph, 43 on the ring with 3 rounds, 96 on the star, 114 on the ring with 1 round, 122 on the line; the money barely moves (all within 0.23% of the hub's equity) because a capped solve is still close to the optimum. Cutting every solve to 200 iterations costs about 0.025 Sharpe and 3% of final equity on both the hub (-2.8%) and the ring (-3.5%); the ring loses a little more, as expected from its less converged positions.

**Recommendation rule.** Threshold: no more than 27 + 13.5 = 40.5 capped rebalances. Only the complete graph with 1 round qualifies (29); the ring with 3 rounds just misses (43), and the ring with 1 round, which uses the fewest messages (46,160), hits the cap at 114 rebalances. **By the rule, the default for the resilience experiments is the complete graph with 1 gossip round.**

## Findings
1. **Network shape governs the communication, not the outcome.** On real data every uncapped topology gives the same system as the hub (B1). The price of a sparse graph is paid in iterations and messages: on simulated problems at eight agents the line needs ten times the iterations of the complete graph (4,000+ against 386), and on real data the line and the ring with one round run out of iterations at 4x as many rebalances as the complete graph.
2. **The pre-registered link between |lambda_2(W)| and iterations failed at four agents (A1).** The ordering holds at eight and sixteen agents and within each problem, but with four agents the problem's own difficulty dominates the topology. We report it as a failure: |lambda_2| explains convergence when the graphs differ enough, not universally.
3. **|lambda_2(W)| predicts better than algebraic connectivity.** The star has the higher algebraic connectivity (1.0 against 0.59 for the ring at M = 8) but is slower (1,183 against 499 iterations), as its larger |lambda_2(W)| (0.88 against 0.80) predicts: with Metropolis weights the hub of a star is a bottleneck.
4. **Removing the hub costs computation that grows with the number of agents.** Every agent solves the system step itself, so the work per iteration is M times the hub's; this experiment took about 3 hours, mostly for sixteen agents (amendment 1).
5. **A short communication budget costs money, little on any topology.** Capping every solve at 200 iterations loses about 3% of final equity and 0.025 Sharpe over five and a half years, the ring slightly more than the hub (A4 agrees: the error at K = 200 is similar across topologies).
6. **Default for the resilience experiments, by the rule: the complete graph with one gossip round.** Caveat for the next experiment's rules: link failures on a complete graph are a weak test (many alternative paths), so the resilience experiment should also include a sparse graph (the ring with 3 rounds, which just missed the rule with 43 capped rebalances against 40.5), declared before any run.
