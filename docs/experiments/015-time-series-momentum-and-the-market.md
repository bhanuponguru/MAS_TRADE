# 015. Time-series momentum as the second agent, and the market of two (Phase 4)

Date: 2026-11-07   Decisions: [0033](../decisions/0033-two-level-mas.md), [0034](../decisions/0034-hypothesis-roster-and-timing.md), [0036](../decisions/0036-risk-model-and-stl-placement.md), [0038](../decisions/0038-beliefs-calibrated-to-the-hypothesis-card.md)
Code: `agents/momentum.py`, `engine.py` (per-agent neutrality, priced volatility limit, specs), `compare_runs.py`, `run_benchmark.py`.
Commands: `uv run python run_benchmark.py --bar B --agents RankCarry|TSMomentum|RankCarry TSMomentum --label NAME` for B in 1d, 4h, 1h, then `uv run python compare_runs.py`.

## Question
Does time-series momentum (H2) add something that carry does not have, and does a market of the two agents beat carry alone?

## Engine changes made for this phase (before any H2 result)
- Neutrality is per agent (carry is dollar- and beta-neutral; H2 owns net exposure), the system net beta is limited to +-0.25 of equity as a priced constraint, and held-but-untradable coins keep their last known beta instead of a placeholder.
- The volatility limit is now a PRICE on the system variance (a term in the joint problem whose multiplier is searched until ex-ante volatility is 20%), not a uniform rescaling of every agent's stake. A uniform rescale makes the agent that adds no variance pay for the one that does (a cross-subsidy); in a solver test at equal total volatility the priced limit left the neutral agent 97% of its unconstrained book (0.073 against 0.075) where the uniform shrink left it 45% (0.034), and the price fell on the factor exposure (halved).
- The calibration spec and the belief-sanity guard are wired into the engine. Both were found to misfire on real data and fixed before any logged run: the calibration spec now acts on the upper confidence bound of the slope (a card-sized belief gives a slope standard error above 1 over 3,000 observations), and the sanity spec tests the volatility-standardised belief (raw beliefs flagged legitimate high-volatility coins). See the changes recorded in [experiment 012](012-mas-levels-on-simulated-data.md).
- Carry alone was re-run (unlogged) after these changes: net Sharpe 1.257 on 1d against 1.272 before (same signal, a different volatility mechanism).

## H2 hypothesis card
See the docstring of `agents/momentum.py`: BTC and ETH only (the literature's per-asset version), trailing 30-day t-statistic, sign +1, kill rule on the pooled slope, not neutral. Magnitude `ic_prior_mean` = 0.05, an assumption. **Mechanical check without P&L (1d):** at the first value tried (0.10) the agent's ex-ante annual Sharpe at its own belief was 1.17 with a mean gross of 0.77 of equity, more than an out-of-sample time-series momentum Sharpe on BTC and ETH can be expected to deliver; the card was revised to 0.05 (about 0.6) BEFORE any P&L run. Only ex-ante quantities were inspected.

## Rules (fixed before any logged run)
**Runs (dev period, each once, 1d / 4h / 1h):** carry alone, H2 alone, carry + H2. Carry alone is re-run in the new engine as the baseline for the paired comparison; it is the same configuration as experiment 013's amended run except for the volatility mechanism, so for the deflated Sharpe it counts as a duplicate of that trial.

**H2 admission (stand-alone runs).** Both required: (a) the intercept of a static regression of H2's net return on the BTC return, annualised, has a 90% moving-block-bootstrap lower bound above 0 on at least two of the three bar sizes (7-day blocks); (b) the same intercept in a regression on BTC and on the carry agent's stand-alone net return has a lower bound above 0 on at least two of three. A timer that only holds market exposure on average fails (a).

**Market acceptance.** Carry + H2 against carry alone, by the paired block-bootstrap Sharpe difference, with the carry-ladder rule of [experiment 014](014-carry-ladder.md): lower bound above 0 on at least two of three bar sizes and no upper bound below 0.

**Reported, not gated:** each agent's final wealth share, beta exposure, carry's gross with and without H2, the specs' activity, bull and bear sub-periods.

**Expected outcome, stated up front.** With fixed card scales and wealth that moves slowly over five years the market should behave roughly like a fixed-weight mix, so "no significant gain over carry" is the likely result and a valid finding. 2020 to 2025 was a strong bull market, which favours any long-biased trend rule; H2's own Sharpe there is not evidence of timing skill, which is why admission is judged on the beta-adjusted intercept.

## Results (dev period, run once each on the final solver; tables in `data/015/`)
**Verdict: H2 fails both admission tests and the market of two is worse than carry alone on all three bar sizes. H2 is not admitted; the carry-alone result of experiment 013 stands.**

| Bar | Run | Net Sharpe | CAGR | Vol | Max drawdown |
|---|---|---|---|---|---|
| 1d | carry alone | 1.26 | 18.9% | 14.6% | -16.0% |
| 1d | H2 alone | **-0.45** | -22.1% | 38.6% | -88.4% |
| 1d | carry + H2 | 0.86 | 15.7% | 19.2% | -32.3% |
| 4h | carry alone | 1.15 | 15.3% | 13.2% | -22.3% |
| 4h | H2 alone | 0.13 | -1.4% | 33.4% | -70.1% |
| 4h | carry + H2 | 0.91 | 14.1% | 16.0% | -29.4% |
| 1h | carry alone | 1.00 | 13.2% | 13.3% | -20.6% |
| 1h | H2 alone | 0.38 | 7.0% | 27.3% | -51.5% |
| 1h | carry + H2 | 0.91 | 13.0% | 14.6% | -25.9% |

**H2 admission (stand-alone runs, annualised intercept with 90% block-bootstrap interval):**
| Bar | beta to BTC | alpha vs BTC | interval | alpha vs BTC and carry | interval |
|---|---|---|---|---|---|
| 1d | -0.02 | -16.1% | -44.8% to +11.4% | -23.2% | -50.9% to +4.2% |
| 4h | -0.03 | +6.2% | -16.0% to +29.0% | +0.6% | -21.2% to +23.5% |
| 1h | -0.03 | +12.0% | -6.6% to +29.5% | +7.7% | -10.6% to +25.7% |
Admission (a) FAILS (the lower bound is above 0 on none of three bars), admission (b) FAILS (none of three).

**Market acceptance (carry + H2 minus carry alone, paired Sharpe difference, 90% interval):** 1d -0.40 (-0.76 to -0.02: significantly worse), 4h -0.24 (-0.68 to +0.20), 1h -0.09 (-0.46 to +0.28). FAIL.

**Reported, not gated.**
- **The market did what it should with a failing agent.** H2's final wealth share fell to 1.9-2.2% (the floor is 2%) on every bar size, carry holding about 98%; the combined result is worse than carry alone because both agents start at equal wealth and H2 lost heavily in 2021-2023 (alone: -61%, -31%, -33% in 2021, 2022, 2023 on 1d) before its share fell.
- **The priced volatility limit spared carry:** carry's gross was 1.72 alone and 1.76 with H2 on 1d (1.63 and 1.78 on 4h, 1.54 and 1.69 on 1h), and its ex-ante Sharpe 0.97 against 0.98; a uniform shrink would have cut it. The beta band bound only rarely (system net beta exposure averaged 0.005-0.014).
- **H2's measured skill is positive, yet it loses money as traded.** The pooled slope of returns on its signal is positive with t = 3.4 (1d), 3.4 (4h), 4.1 (1h) (the BTC and ETH observations overlap and are strongly correlated, so these t-statistics overstate the evidence), and the realised slope (0.029 on 1d) is about five times the card's belief, so the agent was under-confident, not over-confident. Its P&L is nevertheless -22% a year on 1d with a drawdown of -88%, and a volatility of 33-39% against the 20% limit (the limit binds on ex-ante covariance, and BTC and ETH volatility clusters). Explanations are untested: sizing inversely to trailing volatility cuts exposure after booms and raises it in calm periods before crashes; two-coin books are concentrated; and 2021-2023 trends reversed violently. The gate is on P&L, and it is failed.
- **Specs:** no coin belief was zeroed by the sanity spec; the calibration spec reached its minimum multiplier (0.2) for carry in some windows on every bar size (the upper-bound rule fired when a window's slope was strongly negative) and never for H2 (two coins give too few observations: the spec has no power on it); the unconverged cell solves were 31 on 1d, 5 on 4h and 0 on 1h for the combined runs, all with residuals below 1e-3 of the solution (reported as 0.000).

## Findings
1. **Time-series momentum on BTC and ETH, as specified in its card, does not add to carry.** Under the pre-registered rule it is rejected; with the sign and strength fixed in advance its stand-alone result is negative on 1d and weak on 4h and 1h. The BTC beta is about zero, so it is not even a hidden long position: it is a real signal that did not pay as traded. The result sits in a bull market that favours trend rules, which makes the failure less ambiguous, not more.
2. **The wealth market cut H2's capital to the floor, and the system still lost against carry alone** because of the equal starting split. This is the cost of starting from a neutral prior over which agent is right; it was stated as expected ("no significant gain over carry is the likely result"), and the realised outcome is worse: significantly so on 1d.
3. **The priced volatility limit works as designed:** carry's book was not cut when a variance-adding agent joined.
4. **A hypothesis can have a significantly positive pooled signal slope and still fail the gate.** The slope t-statistic is not a trading result: sizing, costs and volatility timing decide it. The gate used P&L, as designed.

## Not done
Timing inside H2's belief (the plan runs a timed against an untimed twin only for agents that pass admission); other hypotheses (cross-sectional momentum, reversal by liquidity bucket, illiquidity, low volatility, CTREND-style trend); the carry ladder's later rungs; the holdout is untouched.

## Changes to rules and process notes (disclosed)
- **The batch was run three times.** The first attempt crashed on the time-series agent in the report (no IC list) after printing its headline; the second was stopped because the 4h runs of H2 were taking over an hour (solver speed, below); the third, on the final solver, is the one reported. Because each aborted attempt finished or half-finished some runs, the trial log (`results/trials.jsonl`, not committed) contains earlier "015" entries for 1d carry alone and for runs that were then repeated with identical settings; for the deflated Sharpe they count once each, not three times.
- **I saw one unlogged headline before the formal H2 runs:** an unlogged timing run of H2 alone on 4h printed "Sharpe 0.125, volatility 33%". No rule was changed afterwards; it is mentioned because the formal runs are not blind to it.
- **Solver work forced by the runs (no change to any rule):** the volatility price and the beta band together made the net-position step 100x slower (three nested root-finders); with a shared-loadings fast path, over-relaxation 1.7 and a penalty of 5x the combined curvature, 1d carry takes 49 s (was 5.5 min) and 4h H2 alone 11 min (was over 90 min, unfinished). A warm start across variance prices had made convergence 8x slower and was removed. The stopping rule was absolute (1e-7) and stopped real problems, whose positions are about 0.01, after about 10 iterations: it is now relative to the size of the cells (1e-6). The NET position is accurate to about 1e-6, the split of the net between agents (offsetting positions cost only their own risk) only to about 9% at that tolerance, so per-agent account attribution carries that noise and the system P&L does not. Carry alone on 1d gave Sharpe 1.257 before and after the change, so experiment 013's baseline is not affected.
