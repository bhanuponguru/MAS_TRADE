# Experiments

Each experiment tests one question behind a decision in [../decisions/](../decisions/).

**Two lines of work.** Experiments 001-010 were run with the legacy implementation (v1 consensus MAS and v2 books/combiners) and describe it as it was: the code is at git tag `legacy-v1-v2` and small reference tables are in [data/](data/). They stay as the record of what was tried and why the system was replaced ([decision 0032](../decisions/0032-replace-v1-v2.md)). Experiments 011 onward belong to the new system.

## Rules
- Write down what each variant does, the exact command, the code version, and the raw CSV location.
- Report the **dev** period (stocks: 2017–2022) and the **test** period (2023–2025) separately. Decide on dev; use test only as a check. For crypto, the last 12 months stay sealed.
- Differences of a few hundredths of Sharpe on one sample are noise. Look at what the option is meant to change (e.g. violations, drawdown) and at what it costs (turnover, return, lines of code).
- End with a recommendation and update the decision's status.

## Index (in the order the experiments were done)
| # | Date | Question | Decisions | Result |
|---|---|---|---|---|
| [001](001-stock-baseline.md) | 2026-10-18 | Does the MAS beat its agents and simple baselines on US stocks? | 0001–0008 | No on return (Sharpe 0.81 vs naive average 0.90); lower drawdown than most agents; capital moves little |
| [002](002-wmsr-vs-admm.md) | 2026-10-18 | W-MSR vs ADMM consensus mode | 0004, 0005 | ADMM = low-vol mean-variance portfolio (Sharpe 0.33); W-MSR stays default |
| [003](003-adversary-resilience.md) | 2026-10-18 | Does W-MSR protect against one compromised agent? | 0004, 0006 | Yes: plain 0.46 -> W-MSR 0.74 (clean 0.81); protection is from trimming, not capital |
| [004](004-hierarchy.md) | 2026-11-01 | Flat vs two-level hierarchy | 0010 | Same Sharpe, lower vol/drawdown/turnover; less resilient under attack |
| [005](005-v1-crypto-benchmark.md) | 2026-11-01, recorded 2026-11-05 | v1 on crypto perps vs BTC, with and without the shield | 0012–0014, 0026, 0030 | No edge over BTC (dev Sharpe -0.03 to 0.61 vs BTC 0.80–1.05); shield cuts vol to 20–26% and halves drawdown; crypto drawdown limit inconsistent (0031) |
| [006](006-v2-dev-findings.md) | 2026-11-01 | v2: which agents/combiners have a net edge? | 0015–0020 | Only funding carry (~1.0) and BTC timing (~0.85); no combiner beats inverse-vol; nothing survives deflated Sharpe |
| [007](007-v2-admm-combiner.md) | 2026-11-05 | v2: does true cost in the ADMM objective cut cost drag? | 0021 | No |
| [008](008-stl-shield-baseline.md) | 2026-11-05 | Phase 1: STL shield and centralised baseline | 0023–0027 | Violations halved or better, MaxDD -26% -> -21%, Sharpe 0.81 -> 0.79 |
| [009](009-intra-period-safety-checks.md) | 2026-11-05 | Should the shield also act between rebalances? | 0028 | Yes: fewer and smaller violations, -0.02 dev Sharpe, +15% turnover. **Adopted** (default on) |
| [010](010-shield-allocation-across-agents.md) | 2026-11-05 | Should the shield cut the riskiest agents instead of all alike? | 0029 | No: no gain without adversary; with one, it spares the adversary. **Code removed** (source in appendix) |

### New system (branch `engine-rebuild`)
| # | Date | Question | Decisions | Result |
|---|---|---|---|---|
| [011](011-data-audit.md) | 2026-11-06 | What data does Binance provide; is the funding formula right? | 0013, 0037 | Funding formula reproduced (corr 0.995); open-interest data from 2020-09 / 2021-12, daily files only; no liquidation data |
| [012](012-mas-levels-on-simulated-data.md) | 2026-11-06 | Do both MAS levels behave as designed on simulated data? | 0033, 0035, 0036 | Phase 1 done: all criteria pass except L1-2 with a wealth floor (selection against over-confidence is unreliable and an unlimited over-confident agent can wipe out the system); A2 restated |
| [013](013-carry-baseline-on-real-data.md) | 2026-11-07 | Does the engine reproduce the legacy carry result on real data? | 0033, 0038 | Yes: net Sharpe 1.27 / 1.12 / 1.00 (1d / 4h / 1h) after fixing belief calibration and the volatility limit; first run 0.48 |
| [014](014-carry-ladder.md) | 2026-11-07 | Does each rung of the carry ladder improve the net dev result beyond noise? | 0034, 0038 | R1 (funding forecast from the premium) rejected at its mechanical gate: worse than the trailing mean at 1d and 4h, not significantly better at 1h; R2 and R3 not run |
| [015](015-time-series-momentum-and-the-market.md) | 2026-11-07 | Does time-series momentum add to carry, and does a market of the two beat carry alone? | 0033, 0034, 0036 | 015a (H2 also held alt hedges, not the card): fails, carry + H2 0.86 / 0.91 / 0.91 against carry 1.26 / 1.15 / 1.00. 015b (card universe BTC/ETH enforced): H2 is admitted (alone 1.06 / 0.95 / 0.90) and carry + H2 reaches 1.59 / 1.62 / 1.57, significantly above carry alone; gains concentrated in 2020-21, forking path disclosed |
| [016](016-timing-inside-h2.md) | 2026-11-07 | Does timing H2's skill by a bull state and a panic state beat the untimed card? | 0039 | No: timed H2 is slightly worse alone (Sharpe 1.03 / 0.90 / 0.86 against 1.06 / 0.95 / 0.90, significantly so on 1d and 4h) and the pair is unchanged (+0.00 to +0.01); timing rejected, code deleted |
| [017](017-reversal-and-the-market-of-three.md) | 2026-11-07 | Is residual reversal an admissible third agent, and does a market of three beat two and a fixed blend? | 0040 | Finished in 018: reversal not admitted (loses net despite a real IC); market of three fails against two, beats the fixed blend of three on 4h and 1h |
| [018](018-rerun-after-volatility-limit-fix.md) | 2026-11-08 | Do the results of 013-017 hold with the corrected volatility limit (a share of current, not initial, equity)? | 0036 | Re-run: carry 1.14 / 1.12 / 0.94; carry + H2 1.39 / 1.48 / 1.48, still beats carry alone, still equal to a fixed blend; **H2 now fails its admission rule** (alpha lower bound > 0 on 1d only); reversal not admitted; market of three below two, but +0.86 / +0.88 above the fixed blend of three on 4h / 1h (wealth cuts the losing agent) |
| [019](019-graph-admm-on-real-data.md) | 2026-11-08 | Does the decentralised (graph, neighbours-only) optimiser reproduce the hub on real data? | 0042 | Yes: market of three on 1d, Sharpe 1.257 / 1.256 / 1.257 (complete / line / line with 3 gossip rounds) against 1.258 for the hub, final equity within 0.3%; the line with one gossip round hits the iteration cap twice as often (43 against 22 of about 137 rebalances) |
| [020](020-topology-and-communication-budget.md) | 2026-11-08 | How does the communication topology change the communication needed, the error under a short budget, and the money made? | 0042 | Rules written; runs pending |

Experiments 001–005 were re-run on 2026-11-05 to recover numbers (the original outputs were not saved). 006–007 quote what was written at the time (v2 is frozen, decision 0022).

## Reproduce
Legacy experiments (001-010): `git worktree add ../mas_trade_legacy legacy-v1-v2` and run the commands in that worktree's README.md. The tables in [data/](data/) are the saved outputs (dev period only; sealed-holdout tables were not copied).
New experiments (011+): commands and committed result CSVs are given in each write-up.
