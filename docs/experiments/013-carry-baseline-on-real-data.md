# 013. The rank-carry baseline on real data (Phase 2 gate)

Date: 2026-11-07   Decisions: [0033](../decisions/0033-two-level-mas.md), [0038](../decisions/0038-beliefs-calibrated-to-the-hypothesis-card.md)
Code: branch `engine-rebuild` (`mas_trade/engine.py`, `agents/carry.py`, `run_benchmark.py`)
Command: `uv run python run_benchmark.py --bar 1d|4h|1h [--label NAME]` (dev period only, holdout sealed). Result tables: `data/013/`.

## Question
Does the new engine (agent beliefs, joint cell ADMM with the cost of the net trade, accounts) reproduce the legacy carry result (net Sharpe about 1.0 on every bar size)? The rank-carry agent is rung 0 of the carry ladder: long low-funding, short high-funding coins by rank, 14-day trailing funding.

## Setup
Broad universe (243 symbols, about 63 members per day), data re-downloaded with the extended columns on 2026-11-06/07, dev period 2020-04 to 2025-11-04 (last 12 months sealed). One agent, so the wealth market is trivial here: this tests the engine, the belief and the cell solver, not the market. Settings (not tuned): Kelly fraction 0.5, margin 3x wealth, gross cap 3x, participation 5% of daily volume, 20% annual volatility limit, fee 5 bp, impact k = 1 at $1M AUM, `min_adv` $1M.

## Results (dev, net of fees, impact and funding)
| Bar | Sharpe | 90% interval | CAGR | Vol | MaxDD | Turnover | Cost drag | Legacy carry book Sharpe (unsmoothed / smoothed) |
|---|---|---|---|---|---|---|---|---|
| 1d | **1.24** | 0.58 to 1.99 | 19.7% | 15.4% | -17.1% | 23.3 | 1.9% | 1.03 / 1.01 |
| 4h | **1.12** | 0.31 to 1.93 | 17.2% | 15.2% | -24.3% | 27.3 | 2.2% | 0.99 / 1.13 |
| 1h | **1.05** | 0.26 to 1.85 | 17.4% | 16.6% | -23.8% | 25.2 | 1.8% | 0.88 / 1.03 |

Annualised P&L components: funding +9.0% / +10.6% / +11.7% and selection +11.6% / +9.1% / +7.3% (1d / 4h / 1h); the market component is about zero (net beta exposure 0.00). Positive in 5 of 6 years on every bar size (1d: 2020 +23%, 2021 +32%, 2022 +7%, 2023 +23%, 2024 +5%, 2025 +20%; the weak year is 2024 on 4h and 1h: -3% and -4%). The realised rank-IC of the carry score is +0.035 (t = 2.2) on 1d, +0.031 (t = 3.5) on 4h and +0.019 (t = 3.4) on 1h, with a hit rate of 53-57%.

**Gate: passed.** The engine reproduces the legacy carry Sharpe on all three bar sizes (equal or higher), with volatility near the 20% limit's neighbourhood, a flat market component and cost drag of about 2% a year.

## What it took to get there (disclosed)
- **First run, 1d: Sharpe 0.48** (CAGR 11%, volatility 37%, drawdown -63%, 25.7 turnover, cost 5.6%). Two causes found from that run, both departures from the design rather than tunable settings: the agent shrank its realised IC toward zero and let the sign float (carry's per-period IC has a 53% hit rate, so its belief flipped sign about half the time: the failure of the legacy IC-weighted fusion, reproduced), and the system volatility limit was not yet enforced (half-Kelly on about 60 coins implies about 50% annual volatility). [Decision 0038](../decisions/0038-beliefs-calibrated-to-the-hypothesis-card.md) fixes both: calibration toward the hypothesis card's prior with its sign fixed, and the volatility limit through the risk aversion.
- This was a second look at the dev period after seeing a result. The trial log (`results/trials.jsonl`, not committed) holds the first run, a duplicate of it (an identical rerun to add the IC table), and the three runs with the fix; the deflated Sharpe must count the first and the fixed variants, not the duplicate.
- The design change moved the Sharpe from 0.48 to 1.24 on one sample, so the number is partly a statement about the fix. The comparison with the legacy book is therefore a regression check, not evidence of an improvement.

## Findings
1. The engine works end to end on real data and reproduces the only known net-positive hypothesis (carry) across bar sizes, with accounting exact (tested) and costs about 2% a year.
2. The selection component carries as much of the profit as funding does, so the carry book is not only a funding harvest. The market component is about zero by construction (agents are beta-neutral).
3. Calibration matters more than the combiner: with the same signal, a belief that can flip sign cost three quarters of the Sharpe.
4. On 1h, 23 of about 900 cell solves hit the iteration cap (unconverged); the gap is small but it is reported, and 1h is the least reliable run.
5. The 90% intervals of the Sharpe exclude zero on every bar size but are wide (lower bounds 0.26-0.58); five years cannot distinguish 1.0 from 1.2.

## Not yet done
Time-series momentum and the other agents; the carry ladder (funding forecast from the premium, crowding term, tail cap); the wealth market with more than one agent; the calibration spec inside the engine; majors universe; unsealing the holdout (once, after the design is frozen).
