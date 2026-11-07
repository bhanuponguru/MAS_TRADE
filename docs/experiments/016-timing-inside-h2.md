# 016. Timing inside H2: timed against untimed (Phase 4)

Date: 2026-11-07   Decision: [0039](../decisions/0039-timing-inside-the-belief-of-h2.md)   Code: `agents/momentum.py` (`TimedMomentum`), `compare_timing.py`
Commands: `uv run python run_benchmark.py --bar B --agents TSMomentumTimed --label "016 timed H2 alone" --tag B_broad_TSMomentumTimed --boot 500` (and `--agents RankCarry TSMomentumTimed` with tag `..._RankCarry+TSMomentumTimed`) for B in 1d, 4h, 1h, then `uv run python compare_timing.py`.

## Question
Does letting H2's skill move with a bull state and a panic state improve it beyond the untimed card, on the same dev data?

## Rules (fixed before any timed run)
- **Runs:** timed H2 alone and carry + timed H2 on 1d, 4h, 1h, each once. The untimed twins are the 015b runs (the same engine; carry alone and 1d H2 alone were re-run on the final code and reproduce).
- **Keep rule (paired block-bootstrap Sharpe difference, timed minus untimed, 7-day blocks, 90% interval):** timing is kept for H2 alone if the lower bound is above 0 on at least two of three bar sizes and no upper bound is below 0 (the ladder rule of experiment 014). The same rule is reported for the carry + H2 pair; the stand-alone comparison decides, the pair is reported.
- **Expectation, stated up front:** the state dependence is estimated from a few hundred noisy periods with a prior that shrinks it by about three quarters, so the likely result is no significant difference and timing rejected. Five years hold few regime episodes. A rejection is a valid finding and the untimed H2 stays.
- **Reported, not gated:** the mean timed IC multiplier (IC / IC0) and its range, fraction of rebalances at the bounds 0 and 2, H2's Sharpe in 2022 (the one bad year).
- One trial for the timed variant; the dev period only; the holdout stays sealed.
