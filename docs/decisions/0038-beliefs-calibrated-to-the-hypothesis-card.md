# 0038. Belief scale comes from the hypothesis card, evidence can only switch an agent off; the system volatility limit is enforced through the risk aversion

Status: **Accepted**   Date: 2026-11-07   Where: `agents/base.py`, `engine.py`, `config.py` (`target_vol`)   Evidence: [exp 013](../experiments/013-carry-baseline-on-real-data.md)

## Context
The first real-data run of the rank-carry agent (1d, dev period) earned a net Sharpe of 0.48 against about 1.0 for the legacy carry book. Two causes, both departures from decisions 0033-0036:
- The agent shrank its realised IC toward ZERO and let the sign float. Carry's per-period IC is noisy (mean +0.035, hit rate 53%), so its belief flipped sign about half the time: the failure of the legacy IC-weighted fusion, reproduced.
- The system volatility limit of 0036 was not yet enforced: half-Kelly on about 60 coins with IC 0.03 implies roughly 50% annual volatility (realised 37%, drawdown -63%).
This was seen on the dev period, so the run is counted as a trial and both versions are reported.

## Decision
- A hypothesis card carries a predicted sign and a small IC magnitude (`ic_prior_mean` = 0.02). The agent's belief is mu = sign x ic_prior_mean x sigma_H x z: the scale is the card's, not an estimate (a trailing IC is too noisy to size bets by).
- Evidence can only switch an agent off: when the expanding-window mean IC in the card's sign has a t-statistic below -2 after at least 20 periods, the agent goes quiet (belief 0, its book unwinds at a cost); it never bets the opposite. Relative stakes between agents are set by wealth.
- The 20% annual volatility limit (the legacy mandate) is enforced through the risk aversion of the joint problem: after a solve, if the ex-ante volatility of the net position exceeds the limit, the Kelly fraction is scaled down and the problem is solved again (at most three times).

## Amendment (2026-11-07, found in review before the multi-agent phase)
The first version of this decision shrank the agent's EWMA IC toward the card's prior with 50 pseudo-observations and clipped it to the card's sign. The EWMA (half-life 12) carries at most about 18 effective observations, so the prior always held about 74% of the posterior: 300 periods of IC -0.04 still gave a belief of +0.004, and the sign clip fired only for ICs below about -0.056. The text above claimed the agent "goes quiet on a bad stretch"; at realistic ICs it did not. The improvement from 0.48 to 1.24 came from the sign clip alone; the vol-limit re-solve rescales the book, so the size of the belief did not matter for one agent, but with several agents prior dominance would give every hypothesis about the same stake. The decision was rewritten as above and the carry runs repeated (Sharpe 1.27 / 1.12 / 1.00 on 1d / 4h / 1h).

## Consequences
Beliefs of an agent with no evidence equal its card prior. An agent whose hypothesis is wrong in sign cannot profit from a flip; that is deliberate (a flip is a different hypothesis and needs its own card).

## Rollback
Make the belief scale an estimate again (an expanding-window posterior with a prior that evidence can outweigh) and drop the kill rule; remove the re-solve loop to drop the volatility limit.
