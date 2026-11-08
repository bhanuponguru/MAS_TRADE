# 0041. H2 (BTC/ETH momentum) stays in the roster as a provisional agent

Status: **Accepted**   Date: 2026-11-08   Where: roster of the experiments (no code change)   Evidence: [exp 015](../experiments/015-time-series-momentum-and-the-market.md), [exp 018](../experiments/018-rerun-after-volatility-limit-fix.md)

## Context
After the volatility-limit fix (experiment 018) the two pre-registered rules about H2 disagree:
- **Admission (015, rule a):** the annualised alpha of H2 alone against BTC needs a 90% lower bound above 0 on at least two of three bar sizes. It is above 0 only on 1d (+0.2%); 4h (-0.9%) and 1h (-2.7%) narrowly miss. The point estimate is about +9% a year on every bar. Before the fix it passed on 1d and 4h, with no margin on 1h.
- **Market acceptance (015):** carry + H2 against carry alone, paired Sharpe difference. It passes on all three bars: +0.26 (+0.04 to +0.47), +0.36 (+0.04 to +0.68), +0.55 (+0.13 to +0.92).

The next block of work (the decentralised optimiser over a communication graph, topology, link failures and a misbehaving agent) studies how agents coordinate, not whether an idea earns money. It needs several agents with different books. Carry, H2 and reversal (as the known-bad agent) are such a set.

## Options
1. **Reject H2** by the admission rule and delete its code. Honest to the rule; leaves carry plus a losing agent, so the coordination experiments would need a simulated second agent.
2. **Admit H2** on the market-acceptance result. That chooses between two rules after seeing which one passes: a forking path, and it would let the report claim an edge the agent's own test does not support.
3. **Keep H2 as a provisional agent:** it stays in the roster and in the coordination experiments, but it is recorded as NOT admitted, and no result may claim that H2 has a proven edge. Its status is decided again in the final run (deflated Sharpe over all trials, and the single look at the sealed holdout), with the admission rule unchanged.

## Decision
Option 3. The admission rule is not changed and not overridden: H2 is "not admitted, provisional". It is used because the coordination experiments need a realistic second agent and H2 is the only one with a positive net return besides carry; the cost of the choice is that every result containing H2 carries the caveat that one of its agents failed its own admission test.

## Consequences
- Reports and the proposal say "carry is admitted; momentum is provisional (fails its stand-alone test narrowly; adds to carry inside the system)". No statement of H2's stand-alone edge.
- The roster for the network, topology and resilience experiments is carry + H2, with reversal as the bad agent.
- The final run reports H2's stand-alone admission test again; if it still fails there, H2 is removed from the final system and the coordination results stay as results about coordination.

## Rollback
Remove H2 from the roster of later experiments (it is a command-line choice of `run_benchmark.py --agents`) and, if rejected for good, delete `agents/momentum.py` (keeping a time-series agent template elsewhere if one is still needed).
