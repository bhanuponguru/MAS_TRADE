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

## Results
(to be filled in as each step is run)

## Changes to rules
None yet.
