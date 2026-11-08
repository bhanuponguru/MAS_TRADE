# 015. Time-series momentum as the second agent, and the market of two (Phase 4)

Date: 2026-11-07   Decisions: [0033](../decisions/0033-two-level-mas.md), [0034](../decisions/0034-hypothesis-roster-and-timing.md), [0036](../decisions/0036-risk-model-and-stl-placement.md), [0038](../decisions/0038-beliefs-calibrated-to-the-hypothesis-card.md)
Code: `agents/momentum.py`, `engine.py` (per-agent neutrality, priced volatility limit, specs), `compare_runs.py`, `run_benchmark.py`.
Commands: `uv run python run_benchmark.py --bar B --agents RankCarry|TSMomentum|RankCarry TSMomentum --label NAME` for B in 1d, 4h, 1h, then `uv run python compare_runs.py`.

> **Re-run on 2026-11-08 ([experiment 018](018-rerun-after-volatility-limit-fix.md)):** the numbers below were computed with a volatility-limit bug (limit measured against the initial, not the current, equity). Corrected numbers and re-applied verdicts are in 018.

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

## Results of 015a (unrestricted universe, as first run; tables in `data/015/`)
**015a verdict: H2 as then implemented failed both admission tests and the market of two was worse than carry alone on all three bar sizes. This was superseded for the card-compliant agent by 015b (below), which reverses it: read 015b for the current verdict on H2.**

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
- **Specs:** no coin belief was zeroed by the sanity spec; the calibration spec reached its minimum multiplier (0.2) for carry in some windows on every bar size (the upper-bound rule fired when a window's slope was strongly negative) and never for H2 (two coins give too few observations: the spec has no power on it); the combined runs had 31 (1d), 5 (4h) and 0 (1h) cell solves that hit the iteration cap; the runner prints their ABSOLUTE residual rounded to three decimals (0.000), so their size relative to the solution (positions are about 0.01) was not recorded and nothing is claimed about it.

## Findings
1. **H2 as implemented in 015a does not add to carry; this is not a verdict on time-series momentum (015b reverses it).** The pre-registered rule rejects it. But a review of what the agent actually held (Amendment 1) shows the book was not the card's: besides BTC and ETH it held hedge positions in other coins, so it was a BTC/ETH trend bet plus a short alt-basket spread, with realised volatility of 39% against a 20% limit. The near-zero BTC beta is the hedge, not evidence about the hypothesis. The card-compliant test is experiment 015b below.
2. **The wealth market cut H2's capital to the floor, and the system still lost against carry alone** because of the equal starting split. This is the cost of starting from a neutral prior over which agent is right; it was stated as expected ("no significant gain over carry is the likely result"), and the realised outcome is worse: significantly so on 1d.
3. **The priced volatility limit works as designed:** carry's book was not cut when a variance-adding agent joined.
4. **A hypothesis can have a significantly positive pooled signal slope and still fail the gate.** The slope t-statistic is not a trading result: sizing, costs and volatility timing decide it. The gate used P&L, as designed.

## Amendment 1 (2026-11-07, after the first results, from a review of H2's footprint; written BEFORE the corrected runs)
**What was found.** On 1d, H2 alone held on average 0.63 of equity gross, of which only about 0.35 was in BTC and ETH (mean |BTC| 0.24, |ETH| 0.11; BTC and ETH had the same sign in 79% of rebalances); the rest, about 0.28, was in other coins. The priced beta band and variance limit make the optimiser neutralise market exposure with an alt basket (a diversified basket looks cheap in a one-factor risk model), so the book was a BTC/ETH trend bet plus a short alt basket. That departs from the card, whose universe is BTC and ETH only: the engine did not enforce a per-agent universe. The one-factor risk model ignores the alts' common residual, which is why the realised volatility (39% on 1d, 33% on 4h, 27% on 1h; 45% at the unused card value 0.10) was far above the 20% ex-ante limit. This is a known gap of the risk model for non-neutral agents (a second, alt-market, factor would be the fix; not built).
**Correction.** The engine now enforces an agent's universe (an agent can only hold the coins in its card). H2 is re-run with that enforced, with the SAME gates, the same card (magnitude 0.05) and no other change. The first results are kept as 015a (unrestricted, as run) and the corrected ones are 015b; both count as trials. The verdict of 015a stands for H2 as it was implemented then; the card-compliant verdict is 015b's.
**Card check on the final solver.** The mechanical check that set the magnitude was repeated on the final solver and does not move: ex-ante annual Sharpe 1.17 at the first value tried (0.10, gross 0.77) and 0.59 at the value used (0.05, gross 0.63) on 1d. Note that the card magnitude is a per-period IC, so the annual ex-ante Sharpe at the same value rises as the holding period shortens (0.59 on 1d, 0.90 on 4h, 1.32 on 1h): the card is not horizon-neutral, a known gap for any time-series agent compared across bar sizes.

## Results of 015b (card universe enforced: H2 holds BTC and ETH only; tables in `data/015/comparison_restricted.csv`)
Exactly as Amendment 1 said: same card (0.05), same gates, same bars, one run each, no other change. Commands: `uv run python run_benchmark.py --bar B --agents TSMomentum [RankCarry TSMomentum] --tag B_broad_<agents>_restricted --boot 500` for B in 1d, 4h, 1h, then `uv run python compare_runs.py --suffix _restricted`.

**Verdict by the pre-registered rules: H2 is admitted (both admission tests pass) and the market of two beats carry alone on all three bar sizes.** Read the caveats below before relying on it.

| Bar | Run | Net Sharpe | 90% interval | CAGR | Vol | Max drawdown |
|---|---|---|---|---|---|---|
| 1d | carry alone | 1.26 | | 18.9% | 14.6% | -16.0% |
| 1d | H2 alone | 1.06 | 0.37 to 1.75 | 12.4% | 11.7% | -12.2% |
| 1d | carry + H2 | **1.59** | 0.92 to 2.30 | 21.9% | 12.9% | -13.8% |
| 4h | carry alone | 1.15 | | 15.3% | 13.2% | -22.3% |
| 4h | H2 alone | 0.95 | 0.28 to 1.60 | 10.9% | 11.5% | -16.3% |
| 4h | carry + H2 | **1.62** | 0.92 to 2.33 | 19.5% | 11.4% | -14.2% |
| 1h | carry alone | 1.00 | | 13.2% | 13.3% | -20.6% |
| 1h | H2 alone | 0.90 | 0.17 to 1.64 | 10.7% | 12.1% | -18.3% |
| 1h | carry + H2 | **1.57** | 0.83 to 2.25 | 18.0% | 10.9% | -14.1% |

**H2 admission (annualised intercept, 90% block-bootstrap interval):**
| Bar | beta to BTC | alpha vs BTC | interval | alpha vs BTC and carry | interval |
|---|---|---|---|---|---|
| 1d | 0.05 | +9.3% | +1.7% to +16.4% | +8.5% | +0.8% to +16.0% |
| 4h | 0.04 | +8.4% | +0.8% to +16.4% | +8.0% | +0.3% to +16.0% |
| 1h | 0.04 | +8.5% | -0.5% to +17.1% | +8.4% | -0.5% to +17.0% |
(a) PASSES (lower bound above 0 on two of three bars, 1d and 4h), (b) PASSES (same two). On 1h the lower bounds are just below zero, so the rule is met with no margin to spare.

**Market acceptance (carry + H2 minus carry alone, paired Sharpe difference, 90% interval; carry alone is the earlier run, and a re-run of 1d carry alone on the final code reproduced it exactly):** 1d +0.34 (+0.10 to +0.59), 4h +0.47 (+0.13 to +0.81), 1h +0.57 (+0.18 to +0.93). PASS (lower bound above 0 on all three).

**Reported, not gated.**
- **The book is now the card's book:** H2 alone has mean gross 0.26 / 0.31 / 0.33 of equity (1d / 4h / 1h), realised volatility 11.7% / 11.5% / 12.1% (inside the 20% limit; 015a's 33-39% is consistent with the alt-hedge explanation of Amendment 1, but its P&L was not decomposed by leg), mean net exposure 0.04, beta to BTC 0.04-0.05. On 1d the system beta band (priced, +-0.25 of equity) was reached (|beta exposure| >= 0.24) at 14% of the rebalances with a position and exceeded at most to 0.30, so it limits H2's size part of the time; the Sharpe is roughly scale-invariant, but the volatility and P&L levels above are set partly by that band and by the volatility limit (binding at 33% of 1d rebalances), not by Kelly alone. (Measured by a re-run of 1d H2 alone on the final code, which reproduced Sharpe 1.061.) Costs are small (0.3-0.5% a year; turnover 7-10).
- **The market no longer cuts H2 to the floor:** final wealth shares of H2 are 35% (1d), 41% (4h), 54% (1h); carry's share is 65% / 59% / 46%. Account P&L on 1d: carry 0.260, H2 0.099 a year (initial equity). Carry's gross (sum of |position| in units of the system's initial equity) is 1.69 / 1.69 / 1.72 with H2, against 1.72 / 1.63 / 1.54 alone, so it did not shrink with its wealth share; the priced volatility limit was binding at 85% / 91% / 96% of rebalances.
- **Yearly net returns (1d):** H2 alone 2020 +16.9% (partial year), 2021 +18.3%, 2022 -5.4%, 2023 +17.9%, 2024 +10.4%, 2025 +12.1%; carry + H2 +29.9%, +38.0%, +5.9%, +25.4%, +8.1%, +15.8%. On 4h H2 alone earned +17.1% and +23.4% in 2020-21 and 2.2-7.8% afterwards; on 1h 12.8% and 26.4% in 2020-21 and 0-12.8% afterwards. Most of H2's return is in 2020-2021.
- **Skill:** the pooled slope of returns on H2's signal is positive (t = 3.4 on 1d, 3.4 on 4h, 4.1 on 1h; overlapping observations on two correlated coins, so these overstate the evidence).
- **Solver:** cells that hit the iteration cap in the H2 runs: 0 (1d), 1 (4h), 15 (1h) for H2 alone; 0 (1d), 0 (4h), 2 (1h) for carry + H2. Their relative residual was not recorded (see 015a).

**Caveats, none of which change the pre-registered verdict.**
1. **This is a forking path.** 015a failed, then the universe was corrected after seeing why. The correction is a fidelity fix to the written card, and it was recorded before the 015b runs, but both runs are trials and a reader should discount accordingly. The deflated Sharpe (not yet computed) must count both.
2. **Two coins, six years, one bull-then-range market.** H2 is BTC and ETH trend; 2020-21 supplies most of the return, and 2022 is flat to negative. A rule-passing result on this sample is not evidence of a durable edge, and the BTC-beta intercept test is the only guard against pure long exposure (beta is near zero here, so the book is not long-biased on average).
3. **The 1h alpha lower bounds are below zero**; admission rests on 1d and 4h, which are the same data at coarser sampling and are not independent evidence.
4. **The card magnitude (0.05) is an assumption** and is not horizon-neutral (ex-ante Sharpe 0.30 / 0.47 / 0.70 at the engine's actual gross on 1d / 4h / 1h); the Sharpe of H2 alone is similar across bars (1.06 / 0.95 / 0.90).
5. **Why the mix beats both alone was not tested.** The likely reason is diversification (H2's beta to BTC is 0.04-0.05 and its correlation with carry was not measured here), which is an explanation, not a result; the gain says nothing about H2's Sharpe in future.
6. Timing inside H2's belief was not run (only for admitted agents, next step).

## Control added after 015b: market against a fixed-weight blend (`compare_blend.py`, `data/015/blend_control.csv`)
Asked after the results: is the gain of carry + H2 over carry alone due to the market, or just to mixing two weakly related return streams? Control: a fixed blend of the two STAND-ALONE net-return series, with weights fixed before looking (50/50, and inverse-volatility, which came out at 0.44-0.48 on carry), against the market run; paired block-bootstrap Sharpe difference, market minus blend, 90% interval.

| Bar | market | 50/50 blend | difference (interval) | inverse-vol blend | difference (interval) |
|---|---|---|---|---|---|
| 1d | 1.59 | 1.61 | -0.01 (-0.30 to +0.27) | 1.60 | -0.01 (-0.35 to +0.34) |
| 4h | 1.62 | 1.48 | +0.14 (-0.16 to +0.43) | 1.47 | +0.15 (-0.18 to +0.46) |
| 1h | 1.57 | 1.35 | +0.21 (-0.11 to +0.57) | 1.35 | +0.22 (-0.13 to +0.59) |

**Reading: the market is not distinguishable from a fixed blend.** On 1d they are equal; on 4h and 1h the market is higher by 0.14-0.22 but every interval contains zero. So the gain of carry + H2 over carry alone (015b) is, on this evidence, diversification of two weakly related agents, which a fixed-weight mix delivers as well. This is the expectation stated in the plan (the structure's value is control, not return) and it is not a failure of the market: the blend uses the two stand-alone runs, each run under its own 20% volatility limit, which the market does not get for free. What the market offers beyond a blend (priced joint limits, netting of trades, wealth moving away from a decaying agent) is not exercised by two agents holding almost disjoint books and has not been demonstrated on real data; it was shown on simulated data (experiment 012).

## Not done
Timing inside H2's belief (H2 is now admitted, so the timed-against-untimed twin is the next step); other hypotheses (cross-sectional momentum, reversal by liquidity bucket, illiquidity, low volatility, CTREND-style trend); the carry ladder's later rungs; the holdout is untouched.

## Changes to rules and process notes (disclosed)
- **The batch was run three times.** The first attempt crashed on the time-series agent in the report (no IC list) after printing its headline; the second was stopped because the 4h runs of H2 were taking over an hour (solver speed, below); the third, on the final solver, is the one reported. Because each aborted attempt finished or half-finished some runs, the trial log (`results/trials.jsonl`, not committed) contains earlier "015" entries for 1d carry alone and for runs that were then repeated with identical settings; for the deflated Sharpe they count once each, not three times.
- **I saw one unlogged headline before the formal H2 runs:** an unlogged timing run of H2 alone on 4h printed "Sharpe 0.125, volatility 33%". No rule was changed afterwards; it is mentioned because the formal runs are not blind to it.
- **Solver work forced by the runs (no change to any rule):** the volatility price and the beta band together made the net-position step 100x slower (three nested root-finders); with a shared-loadings fast path, over-relaxation 1.7 and a penalty of 5x the combined curvature, 1d carry takes 49 s (was 5.5 min) and 4h H2 alone 11 min (was over 90 min, unfinished). A warm start across variance prices had made convergence 8x slower and was removed. The stopping rule was absolute (1e-7) and stopped real problems, whose positions are about 0.01, after about 10 iterations: it is now relative to the size of the cells (1e-6). The NET position is accurate to about 1e-6, the split of the net between agents (offsetting positions cost only their own risk) only to about 9% at that tolerance, so per-agent account attribution carries that noise and the system P&L does not. Carry alone on 1d gave Sharpe 1.257 before and after the change, so experiment 013's baseline is not affected.
