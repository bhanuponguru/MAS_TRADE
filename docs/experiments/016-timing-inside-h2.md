# 016. Timing inside H2: timed against untimed (Phase 4)

Date: 2026-11-07   Decision: [0039](../decisions/0039-timing-inside-the-belief-of-h2.md)   Code: `TimedMomentum` in `agents/momentum.py` and `compare_timing.py`, as at commit 394314e (deleted after this experiment, see Outcome)
Commands: `uv run python run_benchmark.py --bar B --agents TSMomentumTimed --label "016 timed H2 alone" --tag B_broad_TSMomentumTimed --boot 500` (and `--agents RankCarry TSMomentumTimed` with tag `..._RankCarry+TSMomentumTimed`) for B in 1d, 4h, 1h, then `uv run python compare_timing.py`.

## Question
Does letting H2's skill move with a bull state and a panic state improve it beyond the untimed card, on the same dev data?

## Rules (fixed before any timed run)
- **Runs:** timed H2 alone and carry + timed H2 on 1d, 4h, 1h, each once. The untimed twins are the 015b runs (the same engine; carry alone and 1d H2 alone were re-run on the final code and reproduce).
- **Keep rule (paired block-bootstrap Sharpe difference, timed minus untimed, 7-day blocks, 90% interval):** timing is kept for H2 alone if the lower bound is above 0 on at least two of three bar sizes and no upper bound is below 0 (the ladder rule of experiment 014). The same rule is reported for the carry + H2 pair; the stand-alone comparison decides, the pair is reported.
- **Expectation, stated up front:** the state dependence is estimated from a few hundred noisy periods with a prior that shrinks it by about three quarters, so the likely result is no significant difference and timing rejected. Five years hold few regime episodes. A rejection is a valid finding and the untimed H2 stays.
- **Reported, not gated:** the mean timed IC multiplier (IC / IC0) and its range, fraction of rebalances at the bounds 0 and 2, H2's Sharpe in 2022 (the one bad year).
- One trial for the timed variant; the dev period only; the holdout stays sealed.

## Results (dev period, run once each; table in `data/016/comparison.csv`)
**Verdict by the rule: timing is rejected for H2 alone and for the pair. The untimed H2 stays.** Timed H2 is slightly but significantly worse than untimed on 1d and 4h, and its interval straddles zero on 1h.

| Bar | H2 alone untimed | timed | difference (90% interval) | carry + H2 untimed | timed | difference (90% interval) |
|---|---|---|---|---|---|---|
| 1d | 1.061 | 1.031 | -0.030 (-0.049 to -0.009) | 1.594 | 1.597 | +0.002 (-0.004 to +0.010) |
| 4h | 0.953 | 0.900 | -0.053 (-0.093 to -0.015) | 1.619 | 1.629 | +0.011 (-0.006 to +0.027) |
| 1h | 0.904 | 0.855 | -0.048 (-0.126 to +0.044) | 1.567 | 1.580 | +0.013 (-0.025 to +0.056) |

H2 alone, 1d yearly net returns timed against untimed: 2021 +18.5% / +18.3%, 2022 -6.3% / -5.4%, 2023 +17.7% / +17.9%, 2024 +9.7% / +10.4%. The one bad year was not improved by timing.

**Reading.** The pre-registered expectation held: the state dependence cannot be estimated from a few hundred noisy periods, and with the prior's heavy shrinkage the timed belief stays close to the card (the pair differs from the untimed pair by at most 0.013 Sharpe) while the small deviations cost a little on H2 alone. This is a result about this estimator and these two states on this sample, not a proof that H2's skill is state-independent: five years hold few bull/panic episodes and the test has little power against a modest effect. Not reported (not instrumented): the mean timed IC multiplier and the share of rebalances at its bounds; the near-identical pair results suggest the multiplier stayed near 1, but that was not measured.

## Outcome
`TimedMomentum`, its tests and `compare_timing.py` were deleted (replacement rule, decision 0032); the commit above reproduces the runs. The state-dependent skill estimator `agents/timing.py` stays (validated on simulated data, experiment 012). One trial was added to the trial log (label "016 timed H2 alone" and "016 carry+timed H2" on each bar).
