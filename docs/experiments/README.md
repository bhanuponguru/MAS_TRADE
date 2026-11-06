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

Experiments 001–005 were re-run on 2026-11-05 to recover numbers (the original outputs were not saved). 006–007 quote what was written at the time (v2 is frozen, decision 0022).

## Reproduce
Legacy experiments (001-010): `git worktree add ../mas_trade_legacy legacy-v1-v2` and run the commands in that worktree's README.md. The tables in [data/](data/) are the saved outputs (dev period only; sealed-holdout tables were not copied).
New experiments (011+): commands and committed result CSVs are given in each write-up.
