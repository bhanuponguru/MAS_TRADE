# 013. The rank-carry baseline on real data (Phase 2 gate)

Date: 2026-11-07   Decisions: [0033](../decisions/0033-two-level-mas.md), [0038](../decisions/0038-beliefs-calibrated-to-the-hypothesis-card.md)
Code: branch `engine-rebuild` (`mas_trade/engine.py`, `agents/carry.py`, `run_benchmark.py`)
Command: `uv run python run_benchmark.py --bar 1d|4h|1h [--label NAME]` (dev period only, holdout sealed). Result tables: `data/013/`.

> **Re-run on 2026-11-08 ([experiment 018](018-rerun-after-volatility-limit-fix.md)):** the numbers below were computed with a volatility-limit bug (limit measured against the initial, not the current, equity). Corrected numbers and re-applied verdicts are in 018.

## Question
Does the new engine (agent beliefs, joint cell ADMM with the cost of the net trade, accounts) reproduce the legacy carry result (net Sharpe about 1.0 on every bar size)? The rank-carry agent is rung 0 of the carry ladder: long low-funding, short high-funding coins by rank, 14-day trailing funding.

## Setup
Broad universe (243 symbols, about 63 members per day), data re-downloaded with the extended columns on 2026-11-06/07, dev period 2020-04 to 2025-11-04 (last 12 months sealed). One agent, so the wealth market is trivial here: this tests the engine, the belief and the cell solver, not the market. Settings (not tuned): Kelly fraction 0.5, margin 3x wealth, gross cap 3x, participation 5% of daily volume, 20% annual volatility limit, fee 5 bp, impact k = 1 at $1M AUM, `min_adv` $1M.

## Results (dev, net of fees, impact and funding; amended decision 0038)
| Bar | Sharpe | 90% interval | CAGR | Vol | MaxDD | Turnover | Cost drag | Legacy carry book Sharpe (unsmoothed / smoothed) |
|---|---|---|---|---|---|---|---|---|
| 1d | **1.27** | 0.59 to 2.01 | 19.8% | 15.1% | -16.6% | 23.3 | 2.0% | 1.03 / 1.01 |
| 4h | **1.12** | 0.31 to 1.93 | 16.9% | 14.9% | -24.3% | 27.0 | 2.1% | 0.99 / 1.13 |
| 1h | **1.00** | 0.24 to 1.77 | 16.5% | 16.7% | -24.4% | 27.6 | 2.0% | 0.88 / 1.03 |

Annualised P&L components (1d / 4h / 1h): funding +8.8% / +10.6% / +12.4%, selection +11.8% / +8.6% / +6.1%, market about zero (net beta exposure 0.00). Yearly returns, 1d: 2020 +25%, 2021 +32%, 2022 +8%, 2023 +25%, 2024 +5%, 2025 +16%; on 4h and 1h 2024 is -5%. The realised rank-IC of the carry score is +0.035 (t = 2.2) on 1d, +0.031 (t = 3.5) on 4h and +0.019 (t = 3.4) on 1h, with a hit rate of 53-57%. All cell solves converged on all three bar sizes.

**Gate: passed.** The engine reproduces the legacy carry Sharpe on all three bar sizes (equal or higher on 1d and 4h, 1.00 against 0.88 / 1.03 on 1h), with a flat market component and cost drag of about 2% a year.

## What it took to get there (disclosed)
- **First run, 1d: Sharpe 0.48** (CAGR 11%, volatility 37%, drawdown -63%, 25.7 turnover, cost 5.6%). Two causes found from that run, both departures from the design: the agent shrank its realised IC toward zero and let the sign float (carry's per-period IC has a 53% hit rate, so its belief flipped sign about half the time: the failure of the legacy IC-weighted fusion, reproduced), and the system volatility limit was not yet enforced (half-Kelly on about 60 coins implies about 50% annual volatility).
- **First fix (1.24 / 1.12 / 1.05) had a flaw found in review:** it shrank toward the card's prior with 50 pseudo-observations while the EWMA of ICs carried at most about 18 effective observations, so evidence could never move the belief (300 periods of IC -0.04 still gave a belief of +0.004). The improvement came from the sign clip alone, and the vol-limit re-solve hid the missing scale. [Decision 0038](../decisions/0038-beliefs-calibrated-to-the-hypothesis-card.md) was amended: the belief scale is the card's, and a separate pre-registered kill rule (expanding-window IC t-statistic below -2 in the card's sign after 20 periods) switches the agent off. The table above is the amended version; the first-fix numbers were 1.24 / 1.12 / 1.05.
- This was a second and third look at the dev period after seeing results. The trial log (`results/trials.jsonl`, not committed) holds: the first run (plus an identical duplicate that added the IC table), the first fix on three bars, and the amended version on three bars. For the deflated Sharpe the first run, the first fix and the amended version count as three variants of the calibration choice, not nine.
- The move from 0.48 to about 1.2 on one sample says the calibration fix matters; the comparison with the legacy book is a regression check, not evidence of an improvement.

## Findings
1. The engine works end to end on real data and reproduces the only known net-positive hypothesis (carry) across bar sizes, with accounting exact (tested) and costs about 2% a year.
2. The selection component carries as much of the profit as funding does, so the carry book is not only a funding harvest. The market component is about zero by construction (agents are beta-neutral).
3. Calibration matters more than the combiner: with the same signal, a belief that can flip sign cost about 60% of the Sharpe (0.48 against 1.2).
4. In the first-fix run, 23 of about 900 cell solves on 1h hit the iteration cap; with the amended calibration none did on any bar size (the cap depended on the scale of the stakes), so the count is a property of the settings, not a defect of the data.
5. The 90% intervals of the Sharpe exclude zero on every bar size but are wide (lower bounds 0.26-0.58); five years cannot distinguish 1.0 from 1.2.

## Known gaps before the multi-agent phase
- `run_engine` forces dollar- and beta-neutrality on every agent; a time-series momentum agent (which owns net exposure) needs per-agent row constraints, the system beta band, a time-series calibration (rank-IC is cross-sectional) and beta-adjusted reporting first.
- The calibration spec and the belief-sanity guard (decisions 0033, 0036) are not wired into the engine yet.
- With one agent the wealth market is trivial; relative stakes between agents will depend on the card priors and wealth, which is untested on real data.

## Not yet done
Time-series momentum and the other agents; the carry ladder (funding forecast from the premium, crowding term, tail cap); the wealth market with more than one agent; the calibration spec inside the engine; majors universe; unsealing the holdout (once, after the design is frozen).
