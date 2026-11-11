# 018. Re-run of experiments 013, 015b and 017 with the corrected volatility limit

Date: 2026-11-08   Decision: [0036](../decisions/0036-risk-model-and-stl-placement.md) (amendment of 2026-11-08)   Fix: commit `dcacc5d`
Code: `engine.py`, `summarize_runs.py`, `compare_runs.py`, `compare_blend.py`, `compare_reversal.py`
Commands (dev period only, holdout sealed; each run once, labels end in "(vol fix)" in the trial log):
```
uv run python run_benchmark.py --bar B --agents A [A ...] --label "<exp> <name> (vol fix)" --tag B_broad_<tag> --boot 500
#   for B in 1d 4h 1h and (agents -> tag): RankCarry -> RankCarry; TSMomentum -> TSMomentum_restricted;
#   RankReversal -> RankReversal; RankCarry TSMomentum -> RankCarry+TSMomentum_restricted;
#   RankCarry TSMomentum RankReversal -> RankCarry+TSMomentum+RankReversal
uv run python summarize_runs.py                 # data/018/runs.csv, data/018/yearly.csv
uv run python compare_runs.py --suffix _restricted   # data/015/comparison_restricted.csv
uv run python compare_blend.py                  # data/015/blend_control.csv
uv run python compare_reversal.py               # data/017/comparison.csv
```
The tables of the earlier runs are kept as `data/013/summary_pre_volfix.csv`, `data/015/*_pre_volfix.csv`.

## Why
The engine compared the system's ex-ante volatility, measured in units of the INITIAL equity, with the 20% limit, while Kelly stakes grow with wealth; the gross cap and the beta band already scaled with current equity. The effective limit was 20% / (equity multiple): on carry + H2 (1d) realised volatility fell from 20% in 2021 to 8% in 2025, and an agent that lost money got a limit far above 20% of what it had left. Every result of experiments 013-017 was computed under that bug. Nothing else changed: same agents, cards, gates, settings, data and dev period. Experiment 016 (timing inside H2) cannot be re-run because its rejected code was deleted; its verdict was a comparison within the same engine and stands as a comparison under the old limit. Experiment 014 (carry ladder rung R1) likewise.

## Results (dev, net of fees, impact and funding)
| Bar | Run | Sharpe before fix | **Sharpe after fix** | 90% interval | CAGR | Vol | Max DD | Turnover | Annual cost |
|---|---|---|---|---|---|---|---|---|---|
| 1d | carry | 1.26 | **1.14** | 0.36 to 1.90 | 26.1% | 22.6% | -27.7% | 18.9 | 3.4% |
| 1d | H2 | 1.06 | **0.96** | 0.24 to 1.61 | 12.6% | 13.3% | -14.1% | 5.6 | 0.4% |
| 1d | reversal | -0.57 | **-0.66** | -1.29 to -0.03 | -20.7% | 28.7% | -74.7% | 44.6 | 5.9% |
| 1d | carry + H2 | 1.59 | **1.39** | 0.61 to 2.09 | 31.2% | 21.1% | -23.7% | 17.5 | 3.2% |
| 1d | carry + H2 + reversal | 1.42 | **1.26** | 0.52 to 1.97 | 25.9% | 19.9% | -22.1% | 17.3 | 2.9% |
| 4h | carry | 1.15 | **1.12** | 0.36 to 1.87 | 22.0% | 19.5% | -29.8% | 20.2 | 3.0% |
| 4h | H2 | 0.95 | **0.80** | 0.08 to 1.50 | 11.1% | 14.5% | -19.6% | 8.9 | 0.6% |
| 4h | reversal | -1.08 | **-1.17** | -1.82 to -0.48 | -27.3% | 24.7% | -83.8% | 78.9 | 8.9% |
| 4h | carry + H2 | 1.62 | **1.48** | 0.79 to 2.15 | 29.8% | 18.9% | -24.4% | 19.0 | 2.8% |
| 4h | carry + H2 + reversal | 1.39 | **1.34** | 0.66 to 2.01 | 25.5% | 18.3% | -24.0% | 19.1 | 2.7% |
| 1h | carry | 1.00 | **0.94** | 0.25 to 1.67 | 17.3% | 19.0% | -31.1% | 20.1 | 2.5% |
| 1h | H2 | 0.90 | **0.76** | -0.03 to 1.44 | 10.9% | 15.3% | -25.2% | 9.2 | 0.6% |
| 1h | reversal | -0.83 | **-0.99** | -1.63 to -0.32 | -23.5% | 24.1% | -78.6% | 90.8 | 9.5% |
| 1h | carry + H2 | 1.57 | **1.48** | 0.76 to 2.22 | 29.2% | 18.4% | -25.9% | 19.2 | 2.4% |
| 1h | carry + H2 + reversal | not run | **1.33** | 0.64 to 2.03 | 25.4% | 18.3% | -26.2% | 19.1 | 2.4% |

Yearly returns in `data/018/yearly.csv`. Turnover is now per current equity (it was per initial equity before the fix, so the old figures are not comparable).

### The pre-registered verdicts, re-applied
**Experiment 013 (carry baseline):** passes (Sharpe 1.14 / 1.12 / 0.94, within the legacy carry range 0.88-1.13 on 4h and 1h and above it on 1d). The cost drag rises from about 2% to 2.5-3.4% a year because the book is now at its full risk.

**Experiment 015b, H2 admission: now FAILS.** Annualised alpha of H2 alone (90% interval):
| Bar | alpha vs BTC | interval | alpha vs BTC and carry | interval |
|---|---|---|---|---|
| 1d | +9.2% | **+0.2%** to +17.7% | +8.6% | -0.3% to +17.3% |
| 4h | +9.1% | -0.9% to +18.5% | +8.5% | -1.5% to +18.0% |
| 1h | +9.2% | -2.7% to +19.7% | +9.0% | -2.8% to +19.4% |

Rule (a) needs a lower bound above 0 on two of three bars: only 1d, so FAIL; (b) FAIL (none). Before the fix both passed on 1d and 4h with lower bounds of +0.3% to +1.7%. The point estimates barely moved (about +9% a year); the intervals widened because H2's book now runs at 13-15% volatility instead of 11-12%. The 015b verdict "admitted" was already marginal (no margin on 1h), and it does not survive the correction.

**Experiment 015b, market acceptance (carry + H2 minus carry alone): still PASSES.** +0.26 (+0.04 to +0.47) on 1d, +0.36 (+0.04 to +0.68) on 4h, +0.55 (+0.13 to +0.92) on 1h.

**Experiment 015 control (market minus fixed blend of the stand-alone runs): still not distinguishable.** Inverse-volatility blend: 1d -0.07 (-0.45 to +0.32), 4h +0.14 (-0.19 to +0.48), 1h +0.29 (-0.05 to +0.65); the 50/50 blend gives the same picture (1h +0.29, -0.02 to +0.60). The market is ahead on the two faster bars, but no interval excludes 0.

**Experiment 017, reversal admission: NOT admitted.** (a) FAIL (Sharpe lower bound below 0 on every bar); (b) PASS (rank IC 0.025 / 0.042 / 0.046, t 1.5 / 4.4 / 7.3); (c) FAIL (alpha against BTC, carry and H2 is negative, -12% to -23% a year). Same verdict as before the fix.

**Experiment 017, market acceptance (three agents minus two): FAILS.** -0.14 (-0.29 to +0.02) on 1d, -0.14 (-0.31 to +0.02) on 4h, -0.15 (-0.27 to -0.04) on 1h. Adding reversal makes the market worse.

**Experiment 017, reported: market of three against the fixed inverse-volatility blend of the three stand-alone runs.** +0.35 (-0.17 to +0.84) on 1d, **+0.86 (+0.31 to +1.35) on 4h, +0.88 (+0.34 to +1.39) on 1h**. The market cuts the losing agent: reversal's final wealth share is 1.9% / 1.8% / 2.0% (the 2% floor), its account loses 7-9% of initial equity a year, while a fixed blend keeps its weight constant. Annual cost: market 2.9% / 2.7% / 2.4% against blend 2.5% / 3.5% / 3.5%.

## Findings
1. **The bug mattered.** With the limit fixed, every multi-agent run sits at 18-21% realised volatility in every year, as the mandate says; Sharpe ratios fall by 0.03 to 0.2 (more risk costs more and holds the weaker part of each signal), returns rise (carry + H2 CAGR 29-31% instead of 18-22%).
2. **H2 is no longer admitted by its own pre-registered rule**, while the market that contains it still beats carry alone. These two rules now disagree. Resolved by [decision 0041](../decisions/0041-h2-kept-as-provisional-agent.md): H2 stays NOT admitted (the rule is unchanged) but is kept as a provisional agent for the coordination experiments, with no claim of its edge; it is re-judged in the final run.
3. **The "risk model underestimates risk" finding of experiments 015a and 017 was mostly this bug.** Reversal ran at 45% volatility because it lost money and the fixed-size limit became large relative to its shrinking equity; corrected, it runs at 24-29%, still above 20%, so a smaller gap remains for books that are not tightly neutral.
4. **The clearest real-data evidence for the multi-agent structure so far is protection, not return.** With a bad agent in the roster, the wealth-staked market beats a fixed mix of the same agents by about 0.9 Sharpe on 4h and 1h (intervals above 0), because it moves capital away from the loser. Without a bad agent, the market and the fixed mix are equal.
5. The deflated Sharpe over all logged trials has not been computed.

## Not done
Experiments 014 and 016 were not re-run (their code was deleted when rejected). The deflated Sharpe and the sealed holdout remain for the final run.
