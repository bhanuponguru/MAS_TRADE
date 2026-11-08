# 019. The decentralised (graph) cell ADMM on real data: does it reproduce the hub?

Date: 2026-11-08   Decision: [0042](../decisions/0042-decentralised-cell-admm-over-a-graph.md)   Code: `graph_admm.py`, `engine.py`, `run_benchmark.py`
Commands (dev period, 1d, the three-agent roster of experiment 018):
```
uv run python run_benchmark.py --bar 1d --agents RankCarry TSMomentum RankReversal --boot 500 \
    --consensus graph --topology complete|line [--rounds 3] --tag 1d_broad_three_graph_<topology>[_r3] --label "019 ..."
```
Hub reference: the 018 run `results/1d_broad_RankCarry+TSMomentum+RankReversal`.

## Question
Decision 0042 replaces the hub of the joint optimiser by agents that talk only to their neighbours. On simulated problems it reaches the one-node reference (tests). On real data, with the engine's default tolerance and iteration cap, does it give the same system as the hub?

## Rule (written before the runs)
Pass if the graph runs reproduce the hub run's net Sharpe within 0.01 and its final equity within 1%, on the complete graph and on the line (the least connected graph on three agents; with three agents the ring is the complete graph). This is an implementation check, not a hypothesis: these runs are logged in the trial log but are solver variants of one trial.

## Results
| Run | Net Sharpe | CAGR | Vol | Max DD | Final equity | Max / mean abs daily return difference to the hub | Rebalances hitting the iteration cap (of about 137) | Mean solver iterations |
|---|---|---|---|---|---|---|---|---|
| hub (018) | 1.258 | 25.9% | 19.9% | -22.1% | 3.564 | | 21 | not recorded |
| graph, complete | 1.257 | 25.9% | 19.9% | -22.1% | 3.560 | 6.1e-4 / 7.1e-6 | 22 | 1,504 |
| graph, line, 1 gossip round | 1.256 | 25.8% | 19.9% | -22.1% | 3.554 | 9.7e-4 / 1.0e-5 | 43 | 2,011 |
| graph, line, 3 gossip rounds | 1.257 | 25.9% | 19.9% | -22.1% | 3.559 | 6.8e-4 / 7.7e-6 | 24 | 1,554 |

Agent accounts are the same to the third decimal in every run (annual P&L in initial equity: carry 0.427-0.429, H2 0.101, reversal -0.066; final wealth shares 0.738 / 0.243 / 0.019).

**Verdict: PASS.** Sharpe within 0.002 of the hub and final equity within 0.3% on every topology.

## Findings
1. **The decentralised optimiser reproduces the hub on real data.** The system and every agent's account are the same; the remaining differences (0.001% a day on average) come from solves stopped at the iteration cap, not from the topology.
2. **Communication matters even with three agents.** On the line with one gossip round per iteration, twice as many rebalances hit the iteration cap as on the complete graph (43 against 22); three gossip rounds bring it back to 24. That is the topology effect of decision 0042 on real problems.
3. **The hub itself hits the cap at 21 of about 137 rebalances** (pre-existing, visible now that the count is printed next to the graph runs). The P&L impact is small, as above, but it is a known weakness of the real problems (slow convergence of the split between agents; see the solver notes in `cells_admm.py`). The graph version runs without over-relaxation, which is slower per iteration; that is the price of stability under slow mixing.

## Next
Topology and communication budget as an experiment of their own (more agents, simulated problems first), then link failures, agent dropout and a misbehaving agent with a resilient (W-MSR-style) mixing step.
