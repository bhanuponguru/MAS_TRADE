# 014. The carry ladder (Phase 3)

Date: 2026-11-07   Decisions: [0034](../decisions/0034-hypothesis-roster-and-timing.md), [0038](../decisions/0038-beliefs-calibrated-to-the-hypothesis-card.md)
Code: `mas_trade/funding.py`, `agents/carry.py`; commands under each rung.

## Question
Each rung of the carry ladder adds one piece of mechanism to the agent. Does it improve the net dev result beyond noise, so that its extra code is justified? Rung 0 is the rank-carry baseline of [experiment 013](013-carry-baseline-on-real-data.md).

## Rules (fixed before any rung is run)
**Acceptance.** A rung is compared with the previous ACCEPTED rung on 1d, 4h and 1h (dev period, same dates). It is accepted iff on at least two of the three bar sizes the 90% interval of the paired block-bootstrap Sharpe difference (7-day blocks, `block_bootstrap_sharpe(..., ref=previous)`) has a lower bound above 0, and on none of them the upper bound is below 0. A rejected rung's code is deleted and its result stays in this write-up. Each rung is run once; windows and parameters below are fixed in advance and not tuned.

**Rungs.**
- R1, funding forecast (the funding part of carry, mechanical): the belief of a coin is minus the forecast of the funding its long would pay over the holding period, in return units, with no IC scaling and no rank transform.
- R2, price term (crowding): a ridge on funding z-score, premium z-score and open-interest change, IC-shrunk, added to the belief with the kill rule of decision 0038. Defined in detail before it is run.
- R3, tail cap: a per-coin position cap from the high/low range. Defined in detail before it is run.

**R1 model (fixed).** Binance funding per event is F = P + clamp(I - P, +-c), with P the time-weighted average premium over the interval, I = 0.01% per 8 hours and c = 0.05% ([experiment 011](011-data-audit.md): reproduced to a correlation of 0.995). Forecast at decision time t: premium follows an AR(1) in hours around its own trailing 30-day mean, with the autoregressive coefficient pooled over coins on the history window (information before t only): P(h) = mu + phi^h (p_t - mu). The rate per hour is g(h) = [P(h) + clamp(I - P(h), +-c)] / 8, and the forecast funding sum over the next H bars is the sum of g over the H x (24 / bars per day) hours. Events are assumed to sit on the 8-hour grid (the shortened-interval case is about 1.5% of events in the probe).

**Mechanical gate for R1 (no P&L).** Out-of-sample, on the dev period, at every rebalance date: forecast of the funding sum over the next H bars against the realised sum, for every tradable coin. Compare R1's forecast with rung 0's implicit forecast (trailing 14-day mean funding x horizon) by the cross-sectionally demeaned mean squared error (the agents trade differences between coins). R1 passes iff on at least two of three bar sizes the 90% bootstrap interval (resampling rebalance dates in blocks) of MSE(rung 0) - MSE(R1) has a lower bound above 0. R^2 is reported as 1 - MSE / MSE(zero forecast). R1's P&L run is only done if the gate passes.

## Results
**R1 mechanical gate (run 2026-11-07, `run_funding_gate.py`; table in `data/014/gate.csv`): FAILED, so R1 is rejected and was not run for P&L.**
| Bar | Rebalance dates | Coins per date | R^2 rung 0 (trailing 14-day mean) | R^2 R1 (premium forecast) | MSE0 - MSE1 | 90% interval | Lower bound above 0 |
|---|---|---|---|---|---|---|---|
| 1d | 141 | 58 | -0.068 | **-0.905** | -7.1e-05 | -1.6e-04 to -6.8e-07 | no (R1 significantly worse) |
| 4h | 399 | 58 | +0.069 | **-0.293** | -6.6e-06 | -1.5e-05 to -8.7e-07 | no (R1 significantly worse) |
| 1h | 995 | 58 | +0.084 | +0.159 | +3.4e-07 | -8.9e-07 to 1.8e-06 | no (not significant) |
The gate needs the lower bound above 0 on at least two of three bar sizes; it holds on none. R^2 is the share of the cross-sectional variance of realised funding differences explained.

What the numbers say: at holding periods of 2 to 14 days the AR(1)-premium forecast adds variance without information and is clearly worse than simply extrapolating the trailing mean funding; only at the shortest horizon (2 days, 1h bars) does it look better, and not significantly. Rung 0's own forecast explains almost none of the funding differences at any horizon (R^2 between -0.07 and +0.08), so carry's profit comes from the ranking (the sign and order of the funding differences), not from forecasting their size. A plausible but UNTESTED reason for R1's failure is that the state is the premium of the last hour only, which is noisy; a filtered state might help. That would be a new rung with its own pre-registration and its own trial, not a repair of this one.

**Not run: R2 (price term) and R3 (tail cap).** R2 needs the open-interest data, still downloading (33 of 243 symbols after several hours); R3 needs the high/low columns wired into the panel.

## Code of the rejected rung
The R1 model (`mas_trade/funding.py`), the hourly premium loader (`data.load_premium`, `Panel.prem`), the block bootstrap of a mean and the gate script existed at commit `7e68e43` (the last commit that contains it). Reproduce with `git checkout 7e68e43` and `uv run python run_funding_gate.py`.

## Changes to rules
None yet.
