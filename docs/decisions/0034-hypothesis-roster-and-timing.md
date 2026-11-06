# 0034. One agent per established hypothesis; timing inside the belief

Status: **Accepted (design)**   Date: 2026-11-06   Where: `agents/` (not yet built)

## Context
The v2 agents were ad-hoc signals. Searches found replicated crypto evidence in coins we can trade only for carry and time-series momentum; reversal, illiquidity and size seem to live in small coins our $1M volume floor excludes; low-volatility is mixed; factor-timing evidence is mixed in equities and absent in crypto.

## Decision
- Roster: carry (funding forecast + crowding), time-series momentum, cross-sectional momentum, short-term reversal, illiquidity/size, low-volatility/BAB, CTREND-style trend. Each has a written hypothesis card (claim, mechanism, sign, horizon, liquidity-floored universe, data, test, kill criterion, at most two mechanism-based timing state variables).
- Admission gate (pre-registered): net-of-cost dev Sharpe of the agent's own account with a 90% block-bootstrap interval above 0, out-of-sample IC t > 2, positive alpha against the existing agents' accounts; otherwise floor wealth only.
- Timing (pull / push capital) lives inside the belief: state-dependent skill IC(state) = IC0 + theta.s plus a conditional variance forecast scaling the Kelly stake; wealth dynamics are the slow backup. Each agent runs timed and untimed; timing is kept only if it helps. Timing is itself a trial.
- Each hypothesis and each timing variant counts as one trial for the deflated Sharpe; seeds and model variants do not.

## Findings from simulation (exp 012)
Timing inside the belief (ridge-shrunk state coefficient on the per-period calibration slope) beat its untimed twin by +0.0020 per period (90% interval 0.0009 to 0.0033) when skill depended on an observable state, and cost 5.9% of the return when it did not. Real regimes are fewer and noisier than 20 simulated seeds of 1,000 periods; the real test is the paired timed-versus-untimed run per agent.

## Consequences
Honest expectation: the market mostly holds carry and time-series momentum; timing may add little; several agents will sit at floor wealth.

## Rollback
Drop an agent by removing its module; its trials stay in the trial log.
