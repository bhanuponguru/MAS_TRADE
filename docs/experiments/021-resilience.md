# 021. Resilience of the decentralised optimiser: link failures, an offline agent, a misbehaving agent

Date: 2026-11-08   Decision: [0043](../decisions/0043-resilience-of-the-graph-optimiser.md) (builds on [0042](../decisions/0042-decentralised-cell-admm-over-a-graph.md))   Code: `graph_admm.py`, `engine.py`, `run_resilience.py`, `run_benchmark.py`
Proposal question: *Does the decentralised consensus stay correct when links fail, agents drop out or an agent misbehaves, and does W-MSR protect it?*

## Question
(1) Do random link failures and an offline agent leave the decentralised optimiser's result unchanged (at more communication)? (2) Does detect-and-isolate (the W-MSR test used as a detector, decision 0043) protect the honest agents from an agent that sends false values, on which graphs, and against which lies? (3) What do these failures cost on real data?

## Rules (written and committed before any run)
Disclosure: the mechanisms and the detector's parameters (90% of coordinates, 50 iterations, majority of neighbours) were set on development problems (seeds 0-2) before these rules; the results of that prototype are in decision 0043. This experiment uses fresh problems (seeds 10-12) and real data, and changes no parameter.

**Part A, simulated problems** (`run_topology.problem`, eight agents, every limit binding, as in experiment 020; tolerance 1e-8; cap 4,000 iterations, 1,000 for the undefended liar). Graphs: complete with 1 gossip round (020's default), `ring2` (two nearest on each side) with 3 rounds, ring with 3 rounds. The liar is agent 3; it holds nothing, so the right answer is the optimum of the problem without it. Error = max |X - X*| / mean |X*| on the net position.
- **A1 (gate):** with every edge down with probability q in {0.1, 0.3} in every round, every run on every graph converges and its error is at most 1e-4. q = 0.5 and the extra iterations are reported.
- **A2 (gate):** on the robust graphs (complete and ring2), with the detector on: with no liar nobody is isolated and every run converges; with a liar adding a constant d in {0.001, 0.01, 1.0} to everything it sends, the liar and only the liar is isolated, the run converges and the error is at most 1e-4, in every case.
- **A3 (reported, predicted to fail):** the same on the plain ring (not robust: honest agents isolated, graph disconnected).
- **A4 (reported):** the undefended liar (d = 0.01, plain mixing): error after 1,000 iterations. A noise liar (adds normal noise with standard deviation 0.01, new every iteration) with the detector on the complete graph and ring2: how often it is isolated and the error.
- **A5 (reported, decides the code):** W-MSR trimmed mixing (F = 1) with no attacker on the complete graph and ring2. If the error exceeds 1e-2 in most runs, as in the prototype, trimmed mixing is rejected and its code deleted.

**Part B, real data** (1d, dev period, the eight agents of experiment 020; references are the 020 runs: hub, graph complete 1 round, graph ring 3 rounds).
Runs: (1) graph complete r1 with link failures q = 0.3; (2) graph ring r3 with q = 0.3; (3-5) agent `RankCarry7` (the largest account) offline from 2022-05-01 to 2022-08-31 (the LUNA crash and after) on the hub, graph complete r1 and graph ring r3 (the ring without it is a line); (6) graph complete r1 with the detector on and no liar; (7) graph complete r1 with `TSMomentum30` misbehaving (adds 0.01 to everything it sends), no defence; (8) the same with the detector on; (9) the hub with `TSMomentum30` left out (the right answer for 7 and 8).
- **B1 (gate):** runs 1 and 2 reproduce the 020 hub's net Sharpe within 0.02 and final equity within 2%.
- **B2 (gate):** runs 4 and 5 reproduce run 3 (hub with the same agent offline) within 0.02 Sharpe and 2% final equity, and in each of runs 3-5 the highest ex-ante system volatility at a rebalance inside the offline window is no higher than the highest outside it (the risk limit works as well while an agent is missing; per-rebalance values in `rebal.csv`).
- **B3 (gate):** in run 8 the liar is isolated at every rebalance, no other agent is ever isolated, and the run reproduces run 9 within 0.02 Sharpe and 2% final equity; run 6 isolates nobody and reproduces the 020 complete-graph run within 0.002 Sharpe.
- **B4 (reported):** run 7 against run 9 (what an undefended liar costs); the cost of the offline agent (run 3 against the 020 hub); iterations and capped rebalances of every run.

Expectation, stated up front: A1, A2, B1, B2, B3 pass; A3 fails as the robustness condition predicts; the noise liar is mostly not caught; the undefended liar spoils the solve (capped at every rebalance) and costs money; trimmed mixing is rejected.
