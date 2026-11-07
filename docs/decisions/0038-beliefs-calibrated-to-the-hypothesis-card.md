# 0038. Beliefs are calibrated toward the hypothesis card's prior, with its sign fixed; the system volatility limit is enforced through the risk aversion

Status: **Accepted**   Date: 2026-11-07   Where: `agents/base.py`, `engine.py`, `config.py` (`target_vol`)   Evidence: [exp 013](../experiments/013-carry-baseline-on-real-data.md)

## Context
The first real-data run of the rank-carry agent (1d, dev period) earned a net Sharpe of 0.48 against about 1.0 for the legacy carry book. Two causes, both departures from decisions 0033-0036:
- The agent shrank its realised IC toward ZERO and let the sign float. Carry's per-period IC is noisy (mean +0.035, hit rate 53%), so its belief flipped sign about half the time: the failure of the legacy IC-weighted fusion, reproduced.
- The system volatility limit of 0036 was not yet enforced: half-Kelly on about 60 coins with IC 0.03 implies roughly 50% annual volatility (realised 37%, drawdown -63%).
This was seen on the dev period, so the run is counted as a trial and both versions are reported.

## Decision
- A hypothesis card carries a predicted sign and a small prior IC magnitude. The agent's IC estimate is the posterior mean: its own EWMA IC shrunk toward `sign x ic_prior_mean` (0.02) with 50 pseudo-observations, then clipped to the card's sign. A wrong-signed stretch silences the agent (belief 0); it never bets the opposite. Persistent failure is the card's kill criterion, handled by permission and wealth.
- The 20% annual volatility limit (the legacy mandate) is enforced through the risk aversion of the joint problem: after a solve, if the ex-ante volatility of the net position exceeds the limit, the Kelly fraction is scaled down and the problem is solved again (at most three times).

## Consequences
Beliefs of an agent with no evidence equal its card prior. An agent whose hypothesis is wrong in sign cannot profit from a flip; that is deliberate (a flip is a different hypothesis and needs its own card).

## Rollback
Set `ic_prior_mean = 0` and `sign` free (remove the clip) to restore the earlier calibration; remove the re-solve loop to drop the volatility limit.
