# 0029. How the shield's cut is split across agents

Status: **Superseded by 0032** (was: Accepted): `uniform`; `risk` rejected and its code removed   Date: 2026-11-05   Flag: none (the `safety_alloc` flag was removed with the `risk` code)

## Context
When the shield cuts total exposure, it can scale every agent alike, or take the cut from specific agents. Taking it from "the agents causing the problem" would tie the safety layer to the multi-agent layer (proposal Week 7).

## Options
1. **`uniform`**: every agent keeps the same fraction. Simplest.
2. **`risk`**: cut agents in proportion to their Euler risk contribution `RC_i = b_i' Sigma h / h' Sigma h`; agents that hedge are not cut; bisection makes total vol hit the same target as `uniform`. About 35 lines (`safety.allocate_cut`).
3. `trust`: cut low-trust agents first (uses the existing trust scores). Not tried yet.
4. Move capital away from risky agents via the W^T reallocation (with a cash agent). Not tried: changes capital conservation.

## Decision
Option 1 (`uniform`), based on [experiment 010](../experiments/010-shield-allocation-across-agents.md):
- Without an adversary, `risk` gives the same results as `uniform` (dev Sharpe 0.680 vs 0.676, same violations): extra code, no gain.
- With a compromised agent, `risk` cuts the adversary **least** (keeps 67% of its exposure vs 42–52% for honest agents). A random single-stock bet is mostly idiosyncratic, so it adds little to total variance. Test-period drawdown violations went from 0.3% to 10.5%.
Lesson: variance contribution is not blame. If agent-aware cutting is revisited, try option 3 (trust).

## Consequences
`supervise` takes the system portfolio again (not per-agent books) and returns one scale per stock that every agent applies. That is simpler than the per-agent interface the `risk` option needed.

## Rollback
Re-adding `risk`: the removed `allocate_cut` source is in the appendix of [experiment 010](../experiments/010-shield-allocation-across-agents.md). It needs `supervise` to take per-agent books again (A x N) and return an (A x N) scale.
