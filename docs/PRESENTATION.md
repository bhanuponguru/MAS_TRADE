# Presentation report: Resilient Decentralised Portfolio Consensus

**A multi-agent trading system for Binance USD-M perpetual futures. Research summary for the final presentation.**
Status of the evidence: development period only (April 2020 to November 2025); the final 12 months are sealed and have not been looked at. Nothing has been traded live.
Source of every number: the experiment write-ups in [docs/experiments/](experiments/README.md) (018 to 023 for the final figures) and the committed CSVs in `docs/experiments/data/`.

**How to use this file.** It is laid out as slides. Each slide has a **Key message** (the one sentence the audience should leave with), the **content** (what goes on the slide), and **Say** (speaker notes, including the honest caveat). Section "Questions you will be asked" at the end has prepared answers. Where a slide needs a chart, the data file to plot is named.

---

## Slide 1. Title and the one-sentence answer
**Resilient Decentralised Portfolio Consensus: agents that trade different ideas, coordinate without a central node, survive failures, and obey formal safety rules.**

**Key message.** The multi-agent machinery works and is verified against a central reference; the money result is real for carry but does not yet survive correction for how many things we tried.

Content: team, course (Multi-Agent Systems), date. One line: "We built it, tested it against a central optimiser, tried to break it, and report what held up and what did not."

---

## Slide 2. The problem and why multi-agent
**Key message.** A portfolio is one problem that many specialists (agents) see differently; the question is how to combine them without a single point of control or failure.

Content:
- Crypto perpetual futures on Binance: contracts that track a coin and never expire; longs and shorts pay each other a funding fee every 8 hours.
- A trading idea ("hypothesis") is one way to forecast returns: funding carry, momentum, reversal, and others.
- Real systems need: several ideas, shared costs and risk limits, no single point of failure, robustness to a faulty or malicious component, and formal safety guarantees.
- Course topics used: average consensus, ADMM (distributed optimisation), the wealth-staked market (distributed learning), resilient consensus (W-MSR), signal temporal logic (STL).

Say: Stock-style "one model, one optimiser" hides the multi-agent questions. We kept each agent's idea separate and made the coordination the object of study.

---

## Slide 3. What we built (architecture)
**Key message.** Four layers, each testable against a central reference.

```
 agents (one idea each)        carry · BTC/ETH momentum · reversal
        │ beliefs
        ▼
 Level 1: wealth-staked market  each agent bets Kelly-sized on its own belief; its capital moves with its own results
        │ stakes
        ▼
 Level 2: joint optimiser       ADMM over (agent, coin) cells; priced limits: neutrality, capacity, margin,
        │                       gross cap, BTC-beta band, 20% volatility; cost charged on the NET trade
        ▼
 decentralised version          no hub: agents talk only to neighbours on a graph (average consensus on positions and prices)
        │
        ├─ resilience           link failures, an offline agent, a lying agent; detect-and-isolate (W-MSR test)
        └─ STL monitor + supervisor   per-bar robustness of safety specs; "derisk" and "hold" modes
```
Plus: a point-in-time data pipeline, a sealed holdout, a trial log with the deflated Sharpe, an interactive dashboard.

Say: Level 1 answers "who gets how much capital"; Level 2 answers "how do these bets become one portfolio under shared costs and limits"; the rest tests whether Level 2 survives without a centre and under attack.

---

## Slide 4. How we kept the research honest
**Key message.** Rules were fixed before each run, failures are reported as failures, and the last year of data is locked.

Content:
- Point-in-time universe of 243 coins (including delisted ones); fees, square-root price impact and funding all charged; no lookahead (tested).
- Development period April 2020 to November 2025; the final 12 months are sealed and will be opened once, at the end.
- Pass/fail rules written and committed before the runs of each experiment; amendments recorded with a date and whether any result had been seen.
- Every variant tried goes into an append-only trial log; the deflated Sharpe counts them.
- Rejected code is deleted; the experiment records which commit holds it.

Say: This is why some of our slides say FAIL. They are the pre-registered tests, not the ones we would have chosen.

---

## Slide 5. The agents: three documented ideas
**Key message.** Carry is solid; momentum is marginal; reversal does not pay after costs.

| Idea | In plain words | Result on its own (net Sharpe, daily / 4h / hourly, 90% interval daily) |
|---|---|---|
| **Funding carry** | Hold coins where funding is cheap, short where expensive, equal dollars | 1.14 / 1.12 / 0.94 (daily [0.36, 1.90]) |
| **BTC/ETH momentum** | Follow the 30-day trend of Bitcoin and Ethereum only | 0.96 / 0.80 / 0.76 (daily [0.24, 1.61]); admission rule: narrowly fails, kept as a provisional agent (decision 0041) |
| **Residual reversal** | Buy coins that fell more than the market last week, sell the winners | -0.66 / -1.17 / -0.99; the signal predicts (rank IC 0.025 / 0.042 / 0.046) but costs exceed the gain |

Sharpe = return per unit of risk (about 1 decent, above 2 exceptional). Each agent has a written "card": claim, mechanism, allowed coins, expected edge, kill rule.

Say: Reversal is deliberately kept as the "known bad agent": it lets us test how the market and the safety layer react to a loser. Plot: `docs/experiments/data/018/runs.csv`.

---

## Slide 6. The research path, including the dead ends
**Key message.** Most steps either confirmed a mechanism or rejected an idea; the failures are part of the result.

| # | Experiment | What we asked | Outcome |
|---|---|---|---|
| 011 | Data audit | Is the data store sound, is funding computed as we assume? | Verified (funding rule checked against Binance; data extended) |
| 012 | Both levels on simulated markets | Does the machinery behave when the answer is known? | Yes: joint optimiser = one-node reference; capital moves to the skilled agent; safety specs trigger. Limits: the wealth floor slows removal of a bad agent; the calibration spec only reduces late ruin |
| 013 | Carry in the new engine | Reproduce the legacy carry result | Passes |
| 014 | Improved carry (funding forecast) | Does forecasting funding beat past funding? | No; dropped |
| 015 | Momentum and the market | Admit momentum? Does the market beat carry alone? | First run failed because the agent held coins its card forbids (bug fixed, re-run); market beats carry alone; but equals a fixed mix of the same agents |
| 016 | Timing momentum by market state | Does a bull/panic state improve it? | No (slightly worse); rejected, code deleted |
| 017 | Reversal and the market of three | Admit reversal? | Not admitted; the market is worse with it than without |
| 018 | Re-run after a risk-limit bug | Do conclusions survive the fix? | Numbers moved (Sharpe 0.03 to 0.2 lower); momentum's admission flipped to "narrow fail"; the "risk model is broken" worry was mostly the bug |
| 019-021 | Decentralised optimiser, topology, resilience | Same answer without a hub? Which network? Failures? | See slides 9 to 11 |
| 022 | STL monitor and supervisor | Does it keep the system inside its specs, at what cost? | Partly (slide 12) |
| 023 | Final comparison and deflated Sharpe | One table; does the money survive multiple testing? | Mechanisms yes; money result fails the correction (slide 13) |

Say: The timeline slide is the honest one: ten experiments, three ideas, two bugs found by us.

---

## Slide 7. Money and risk on the development period
**Key message.** The main system (carry + momentum through the market) reaches Sharpe about 1.4 to 1.5 at the risk limit, with about 30% a year.

| Net Sharpe [90% interval] | Daily | 4-hourly | Hourly |
|---|---|---|---|
| carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| momentum | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [-0.03, 1.44] |
| reversal | -0.66 [-1.29, -0.03] | -1.17 [-1.81, -0.48] | -0.99 [-1.63, -0.32] |
| **main system: market of two** | **1.39 [0.61, 2.09]** | **1.48 [0.79, 2.15]** | **1.48 [0.76, 2.22]** |
| market of three (with reversal) | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| 50/50 fixed blend carry + momentum | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

Main system: CAGR 31.2% / 29.8% / 29.2%, volatility 21% / 19% / 18% (limit 20%), maximum drawdown -23.7% / -24.4% / -25.9%. Costs about 2.4% to 3.2% a year.

Say: All figures net of fees, price impact and funding. The intervals are wide: five and a half years is short. Plot: `docs/experiments/data/023/T1_money.csv`.

---

## Slide 8. What the market of agents adds
**Key message.** With good agents the market equals a fixed mix; with a bad agent it protects.

- Market of two vs carry alone: +0.26 / +0.36 / +0.55 Sharpe (all intervals above 0): adding momentum helps.
- Market of two vs a fixed blend of the stand-alone runs: -0.07 / +0.14 / +0.29, no interval excludes 0: **the gain over carry alone is diversification, which any mix gives.**
- With reversal in the roster, market of three vs the fixed blend of the three: +0.35 (n.s.) / **+0.86 [0.31, 1.35]** / **+0.88 [0.34, 1.39]** on daily / 4h / hourly. The market cut reversal's capital to the 2% floor (final share 1.9% / 1.8% / 2.0%); a fixed blend kept paying for it.

Say: This is the cleanest real-data evidence that the staked market earns its place: protection from a failing agent, not extra return. Caveat: the fixed blend here uses full-sample volatilities for its weights, and adding reversal still leaves the market of three below the market of two (-0.14 to -0.15). Source: experiments 015 and 018; `data/015/blend_control.csv`, `data/017/comparison.csv`.

---

## Slide 9. Removing the hub: the decentralised optimiser
**Key message.** With no central node, agents reach the same portfolio as the central optimiser.

How: each agent keeps its own estimate of the group's net position and its own price; neighbours mix them step by step (dynamic average consensus, Metropolis weights) while each solves its own part of the ADMM. Graphs available: complete, ring, line, star, random.

Result on real data (daily, three agents, experiment 019): hub Sharpe 1.258, graph complete 1.257, line 1.256, line with three gossip rounds 1.257; final equity within 0.3% of the hub; every agent's account the same to three decimals. **PASS.** Cost: on the line with one gossip round, twice as many rebalances hit the iteration cap (43 vs 22); three rounds bring it back to 24.

Say: The decentralised solver is slower and heavier (each agent solves the system step itself), but not different in outcome. Source: `docs/experiments/019-graph-admm-on-real-data.md`.

---

## Slide 10. Does the network shape matter?
**Key message.** Shape decides how much communication you need, not what answer you get.

Simulated problems (experiment 020; median iterations to converge at 3 gossip rounds):

| Agents | complete | ring | random | star | line |
|---|---|---|---|---|---|
| 4 | 151 | 165 | 228 | 264 | 389 |
| 8 | 386 | 499 | 883 | 1,183 | 4,000 (none converged) |
| 16 | 1,000 | 3,709 (2 of 3 converged) | 1,000 | 4,000 (none) | 4,000 (none) |

- The mixing rate (second-largest eigenvalue of the mixing matrix) predicts iterations at 8 and 16 agents (Spearman 0.90 and 0.78), **but the pre-registered threshold of 0.7 failed at 4 agents (0.60)**: the problem's own difficulty dominated; within each problem the ordering held (0.79 to 0.96).
- It predicts better than algebraic connectivity: the star has higher connectivity than the ring but is slower, because with Metropolis weights its centre is a bottleneck.
- Real data, eight agents (variants of the three ideas): every uncapped topology within 0.002 Sharpe and 0.23% of the hub's final equity; rebalances at the iteration cap 27 (hub) to 122 (line). Cutting every solve to 200 iterations costs about 0.025 Sharpe and 3% of final equity.
- By the pre-registered rule the default is the complete graph with one gossip round.

Say: A reviewer will ask about the failed gate: we report it as a failure and explain it (small graphs, difficulty dominates), we do not redefine it. Plot: `data/020/partA_summary.csv`, `data/020/partB_runs.csv`.

---

## Slide 11. When things break: resilience
**Key message.** Failures cost communication, not money; a consistent liar is caught on a robust graph; a stealthy one is not.

| Failure (real data unless noted) | Result against the right reference |
|---|---|
| 30% of links down each round | Sharpe within 0.001; ring needs 15% more iterations (60% more on simulated problems) |
| Largest agent offline four months (through the LUNA crash) | Equal to the central version with that agent offline; the cost is the missing agent: -0.015 Sharpe, -2.8% final equity |
| A liar adding a constant, detector on (complete graph, ring2) | Liar isolated at the first rebalance and only the liar; equals the run without it (1.182 vs 1.182); detected from 4% of a typical position upward in 18 of 18 simulated runs |
| Same on the plain ring | Fails as predicted: honest agents isolated too (robustness of the graph, not just connectivity, decides) |
| A noise liar (random lies) | Caught in only 1 of 6 simulated runs; otherwise the solver does not converge |
| W-MSR trimmed averaging inside the optimiser | **Rejected:** it breaks convergence even with no attacker (errors 50% to 480%), because it throws away part of the sum the agents track. Its code was deleted |

Say: The lecture's W-MSR cannot be dropped into this optimiser, but its test works as a detector. A stealthy liar is exactly where the next layer (the supervisor) is needed. Source: experiment 021.

---

## Slide 12. Formal safety: STL monitor and supervisor
**Key message.** The monitor tells where the system was in danger and de-risking limits drawdowns, at a price; one of our supervisors needs a better limit.

- A record per bar of how far each spec is from violation: volatility, 365-day drawdown, realised volatility with 14-day recovery, solver health. Limits come from decision 0026, argued before any run.
- The tightest stress window was the **FTX collapse (Nov 2022 to Jan 2023)**, not May 2021 or LUNA as expected.
- **Derisk** (shrink the risk target after drawdowns): worst 365-day drawdown -19.7% / -18.8% / -16.7% against -23.7% / -24.4% / -25.9% without it; Sharpe cost -0.12 / -0.20 / -0.02. Gate A2 passes on 4h and hourly, **fails on daily** (more bars below the line because recovery is slower).
- **Volatility spec gate A1 fails on hourly** (94.3% of rebalances within 1.05 times target against the 95% gate): the price search lags fast-moving covariance.
- **Hold** (trade nothing on an unsafe solve): stops the noisy liar's corrupted solves (all six in the window held), but with its pre-fixed residual limit of 1e-3 it also froze nine honest, slowly converging solves in 2025: Sharpe 1.03 against 1.26. Decision 0044: derisk usable, hold off by default until its limit is re-argued. The two cases differ in residual by a factor of about 300, so a better limit exists.

Say: Present A1, A2 and B1 as the findings they are: "pre-registered gates failed; here is why". Source: experiment 022; `data/022/runs.csv`, `data/022/windows.csv`.

---

## Slide 13. The final comparison and the multiple-testing verdict
**Key message.** The mechanisms equal the central reference; the money result does not yet pass the deflated Sharpe.

- **C1 (consistency): PASS.** Every figure shared with experiments 018 to 022 reproduces to 0.001.
- Centralised vs decentralised, all topologies, failures, an offline agent and an isolated liar: within 0.002 Sharpe of the hub; they cost messages (up to 2.7 times) and capped rebalances (up to 4.5 times on a line).
- **C2: FAIL on every bar size.** Deflated Sharpe of the main system: **0.070 / 0.100 / 0.101** at the 45 strategy trials we counted (0.031 / 0.046 / 0.047 counting all 74 engineering variants too); the bar is 0.95. It stays above 0.95 only up to about 2 trials.
- Why: 45 strategies of widely spread quality (Sharpe -1.2 to 1.5) and only five and a half years; a best Sharpe of 1.4 to 1.5 is what the best of that many tries would show by chance with probability about 90%.
- What it does not mean: the intervals for carry stay above zero on every bar size. The sealed final year is the independent test the correction cannot replace.

Say: This is a statement about the evidence, not a proof of no edge. Plot: `data/023/T5_curve.csv` (deflated Sharpe against number of trials).

---

## Slide 14. Mistakes we found and fixed (credibility slide)
**Key message.** Four errors surfaced because the rules, the logs and the cross-checks were in place.

1. **Momentum held coins its card forbids** (alt-coin hedges, 39% volatility): found by inspecting the footprint; the engine now enforces each agent's coin list; both runs counted as trials.
2. **The risk limit used starting money instead of current money** (experiment 018): volatility had drifted to 8% in 2025; after the fix every system runs at 18% to 21% in every year; Sharpe moved by -0.03 to -0.2 and momentum's admission flipped.
3. **A monitoring bug in the supervisor** (it recorded the rejected solve's volatility instead of the held positions'): the test now fails on the old code.
4. **A gate designed too blunt:** the hold limit cannot tell an attack from slow honest convergence; reported as failed rather than tuned away.

Say: Two of these changed headline numbers. Each is documented with the commit that fixed it.

---

## Slide 15. Limits and honest caveats
**Key message.** What these results do and do not establish.

- Five and a half years, mostly one bull market; the sealed final year has not been seen. Nothing live.
- Momentum is two coins, most of its profit in 2020 to 2021, and fails its own admission rule narrowly; it is kept as a provisional agent (decision 0041) and re-judged in the final run.
- The money result fails the deflated Sharpe at 45 strategy trials.
- The decentralised optimiser is heavier (each agent solves the system step; the 16-agent topology runs took about 3 hours) and some real-data rebalances stop at the iteration cap (21 to 27 of about 135 even for the hub); the P&L effect is small but real.
- Reversal still runs at 24% to 29% volatility against the 20% limit: a one-factor risk model underprices books that are not tightly neutral.
- Experiments 014 and 016 were not re-run after the risk-limit fix (their code was deleted when rejected).

---

## Slide 16. Interactive dashboard (demo)
**Key message.** The mechanisms can be shown live, not just tabulated.

Run: `uv run --group dashboard streamlit run dashboard.py` then open http://localhost:8501. Six tabs: **consensus simulator** (live decentralised optimiser on simulated problems: choose graph, gossip rounds, link failures, a liar, with or without the detector; shows error against the central optimum, disagreement per iteration, messages, who was isolated); topology and communication (020); performance and agents' wealth (saved runs); STL safety record with the stress windows (022); resilience (021, 022); final comparison (023).

Say: Suggested 3-minute demo: (1) complete graph vs line at 8 agents, watch the error curves; (2) switch on 30% link failures; (3) add a liar without the detector (error stuck), then with the detector (liar isolated, error to zero). The saved-run tabs need the local `results/` folder; on another machine only the committed tables show. Decision 0045.

---

## Slide 17. What is next
**Key message.** The system is built; the remaining work is evidence.

1. The single look at the sealed final year, after the design is frozen, with momentum's admission rule applied unchanged.
2. Re-argue the hold limit before switching it on; a longer volatility-price search for hourly.
3. More ideas, one at a time with a card and rules first: low volatility, a machine-learning trend model, carry variants that use open interest or high/low prices; cross-sectional momentum and size are last (weak evidence here).
4. A second risk factor (alt-coin market) if a non-neutral agent matters.
5. Decide with the co-authors whether and how to merge `engine-rebuild` into `main`.

---

## Slide 18. Summary
**Key message (one slide to leave up during questions).**
- We built a resilient decentralised multi-agent trading optimiser and validated it against a central reference: same portfolio on every network shape, under failures, with an offline agent and with an isolated liar.
- The wealth-staked market of agents does not beat a fixed mix of good agents, but clearly beats a fixed mix when one agent is bad (about +0.9 Sharpe on 4h and hourly).
- STL monitoring shows where the system was in danger (FTX) and derisk limits drawdowns at a Sharpe cost; hold needs a re-argued limit.
- Funding carry is a solid edge; the system's Sharpe of about 1.4 to 1.5 does not survive the deflated-Sharpe correction on the development period alone. The sealed year is the next test.
- We report our failed gates as failed.

---

## Questions you will be asked (prepared answers)
**Is it profitable?** On the development period, net of all costs, the main system makes about 30% a year at about 20% volatility (Sharpe 1.4 to 1.5). After correcting for the 45 variants tried the evidence is not conclusive (deflated Sharpe about 0.1); the sealed final year has not been looked at and is the real test.

**Why not just use one central optimiser?** We did, as the reference. The decentralised version reproduces it to within 0.002 Sharpe; the value is no single point of failure, and the experiments show what it costs (more iterations, messages and compute).

**Did the multi-agent structure add return?** Not over a fixed mix of two good agents (differences not significant). It added protection: with a losing agent present the market beat the fixed mix by about 0.9 Sharpe on 4h and hourly.

**Does W-MSR work?** Not as the averaging rule inside this optimiser (it breaks convergence even without an attacker); its test works as a detector of a consistent liar on robust graphs, but not against random noise. A supervisor catches the noisy case.

**Why do some gates fail?** They were written before the runs and we kept them. The failures (topology correlation at 4 agents, drawdown gate on daily, volatility gate on hourly, hold's false alarms) are each explained in the experiment and none was changed afterwards.

**Is the data free of lookahead and survivorship?** Point-in-time universe with delisted coins; no-lookahead is a tested invariant; bars are stamped with their open time.

**What are the bugs you found?** See slide 14: forbidden-coin holdings, risk limit measured on starting equity, a monitor recording bug.

**What changed from the earlier version?** A clean-slate replacement (decision 0032): the old consensus/W-MSR system and the single-optimiser v2 engine are preserved at git tag `legacy-v1-v2`.

---

## Where to find everything (for the appendix slide)
- Experiments: [011](experiments/011-data-audit.md), [012](experiments/012-mas-levels-on-simulated-data.md), [013](experiments/013-carry-baseline-on-real-data.md), [014](experiments/014-carry-ladder.md), [015](experiments/015-time-series-momentum-and-the-market.md), [016](experiments/016-timing-inside-h2.md), [017](experiments/017-reversal-and-the-market-of-three.md), [018](experiments/018-rerun-after-volatility-limit-fix.md), [019](experiments/019-graph-admm-on-real-data.md), [020](experiments/020-topology-and-communication-budget.md), [021](experiments/021-resilience.md), [022](experiments/022-safety-monitor-and-supervisor.md), [023](experiments/023-final-comparison-on-the-dev-period.md).
- Decisions 0032 to 0045: [decisions index](decisions/README.md) (0042 decentralised optimiser, 0043 resilience, 0044 STL supervisor, 0045 dashboard).
- final table: `uv run python final_table.py`; tests: `uv run pytest`.
- Glossary: *Sharpe* return per unit of risk; *net* after fees, impact and funding; *hub* the central optimiser; *gossip round* one exchange between neighbours; *mixing rate* how slowly a graph spreads information (smaller is faster); *W-MSR* the lecture's robust averaging rule; *STL* signal temporal logic; *derisk / hold* the two supervisor modes; *deflated Sharpe* Sharpe corrected for the number of variants tried; *dev period* data we may decide on; *sealed holdout* the last 12 months.
