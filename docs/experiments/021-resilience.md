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

**Amendment 1 (2026-11-08, after the other runs had finished): run 7 (undefended liar on real data) was stopped after 3 h 40 min without output.** With the lie, every solve runs to the 3,000-iteration cap and the volatility search re-solves up to five more times, so the run would have needed many more hours. It feeds only B4 (reported, no gate); the cost of an undefended liar is shown on the simulated problems (A4) instead. Not in the trial log (it never finished).

## Results, part A (simulated problems, seeds 10-12)
Command: `uv run python -u run_resilience.py --workers 3` (about 3.5 hours beside part B). Table: [data/021/partA.csv](data/021/partA.csv) (one row per run). The A5 rows were produced at commit `4194d43`; trimmed mixing was then deleted (below), so the current script no longer runs them.

**A1 (gate): PASS.** Every run with links down with probability 0.1 or 0.3 converged, with error at most 5.4e-6 (rule: 1e-4). Even at 0.5 every run converged. Median iterations:

| Graph | no failures | q = 0.1 | q = 0.3 | q = 0.5 |
|---|---|---|---|---|
| complete, 1 round | 187 | 215 | 262 | 288 |
| ring2, 3 rounds | 193 | 214 | 235 | 265 |
| ring, 3 rounds | 439 | 513 | 700 | 1,075 |

**A2 (gate): PASS.** On the complete graph and ring2, with the detector on: with no liar nobody was isolated and every run converged; with a liar adding 0.001, 0.01 or 1.0 (from 4% of a typical position upward) the liar and only the liar was isolated in all 18 runs, every run converged, and the error against the optimum without the liar was at most 4.4e-6.

**A3 (reported): failed, as predicted.** On the plain ring, in all 9 liar runs an honest agent was isolated too (mostly agent 5, two steps from the liar) and the graph fell apart. With no liar the ring isolated nobody (3 runs).

**A4 (reported).** Undefended liar (adds 0.01, plain mixing): error after 1,000 iterations 5.5 to 5.9 times a typical position on every graph, and no convergence. Noise liar with the detector: isolated in 1 of 6 runs (complete graph, seed 11, after which the result was exact); in the other 5 runs no isolation, no convergence in 4,000 iterations and error 12.5 to 14.8 times a typical position.

**A5 (reported; decides the code).** W-MSR trimmed mixing (F = 1) with no attacker: no run converged and the error was 0.50 to 4.8 times a typical position (6 of 6 runs above 1e-2). **Trimmed mixing is rejected and its code deleted** (`wmsr_mix`, the `trim` option; at commit `4194d43`).

## Results, part B (real data, 1d, dev period, eight agents)
Commands: as in experiment 020 (`AG=...`, `--boot 500`) with the options listed in the rules, tags `021_<run>`:
```
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 021_links_complete_r1 --consensus graph --topology complete --rounds 1 --link-fail 0.3
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 021_links_ring_r3 --consensus graph --topology ring --rounds 3 --link-fail 0.3
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 021_offline_hub --offline RankCarry7 2022-05-01 2022-08-31
    # 021_offline_complete_r1 / 021_offline_ring_r3: the same with --consensus graph --topology complete --rounds 1 / ring --rounds 3
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 021_detect_clean --consensus graph --topology complete --rounds 1 --detect 50
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 021_liar_detect --consensus graph --topology complete --rounds 1 --faulty TSMomentum30 --attack 0.01 --detect 50
uv run python run_benchmark.py --bar 1d --agents $AG --boot 500 --tag 021_liar_hub --faulty TSMomentum30
```
Table: [data/021/partB_runs.csv](data/021/partB_runs.csv). 135 rebalances.

| Run | Net Sharpe | Final equity | Rebalances at the iteration cap | Mean iterations |
|---|---|---|---|---|
| hub (020) | 1.240 | 3.578 | 27 | 1,427 |
| graph complete r1 (020) | 1.239 | 3.577 | 29 | 1,459 |
| graph ring r3 (020) | 1.239 | 3.575 | 43 | 1,870 |
| (1) complete r1, links down 30% | 1.239 | 3.577 | 31 | 1,692 |
| (2) ring r3, links down 30% | 1.239 | 3.575 | 56 | 2,155 |
| (3) hub, RankCarry7 offline May-Aug 2022 | 1.225 | 3.476 | 28 | 1,440 |
| (4) complete r1, RankCarry7 offline | 1.225 | 3.476 | 29 | 1,468 |
| (5) ring r3, RankCarry7 offline | 1.225 | 3.474 | 46 | 1,902 |
| (6) complete r1, detector on, no liar | 1.239 | 3.577 | 29 | 1,459 |
| (8) complete r1, liar TSMomentum30, detector on | 1.182 | 3.391 | 30 | 1,541 |
| (9) hub without TSMomentum30 | 1.182 | 3.392 | 29 | 1,512 |

**B1 (gate): PASS.** With 30% of links down, Sharpe within 0.001 of the hub and final equity within 0.09%, on the complete graph and the ring.

**B2 (gate): PASS.** The graph runs with the agent offline equal the hub with the agent offline (Sharpe difference 0.000, final equity within 0.06%). In all three runs the highest ex-ante volatility inside the offline window was 17.5%, against 20.9% outside it.

**B3 (gate): PASS.** The liar was isolated at the first rebalance and stayed out for all 135; nobody else was ever isolated; the run equals the hub without the liar (Sharpe 1.182 both, final equity within 0.04%). With the detector on and no liar, nobody was isolated and the run is identical to the 020 complete-graph run (1.239).

**B4 (reported).** The undefended liar on real data was not completed (amendment 1). Losing the largest account (RankCarry7, 38% of final wealth) for four months, including the LUNA crash, costs 0.015 Sharpe and 2.8% of final equity (run 3 against the 020 hub). Leaving TSMomentum30 out costs 0.058 Sharpe and 5.2% of final equity (run 9 against the 020 hub), mostly because its capital then sits idle (it holds nothing but keeps its wealth share). Link failures cost communication, not money: on the ring with 30% of links down the mean iterations rise from 1,870 to 2,155 and capped rebalances from 43 to 56.

## Findings
1. **Link failures and an offline agent are absorbed.** With weights recomputed on the links that are up, the optimiser still reaches the same answer (simulated: every run converged even at 50% failures; real data: Sharpe within 0.001). The cost is communication: on the ring, 30% failures mean 60% more iterations on simulated problems and 15% more on real ones. An agent going offline is the same problem with one agent fewer; network and hub give the same result.
2. **The lecture's W-MSR trimmed averaging cannot be dropped into this optimiser.** It breaks the optimiser even with no attacker (no convergence; errors 50% to 480%), because it discards part of the sum the agents track. Rejected and deleted.
3. **Used as a detector, the W-MSR test works when the graph is robust.** On the complete graph and on ring2 (sparse: four neighbours each), a consistent liar was caught at every size from 4% of a typical position, with no false alarm, on simulated and real data, and the result was exactly the right one. On the plain ring (two neighbours) honest agents were also isolated, as the robustness condition predicts: robustness of the graph, not just connectivity, decides whether the system can defend itself.
4. **A stealthy liar gets through.** Random noise is caught only once in six; otherwise the result is far off and the solver does not converge. Non-convergence is visible, so the safety supervisor (next step) should refuse to trade on a solve that did not converge.
5. **Resilience costs little money when it works.** Every defended failure on real data is within 0.001 Sharpe of the matching reference. The money lost comes from what is missing (an agent out, or idle capital), not from the coordination.
