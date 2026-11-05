# 005. v1 system on crypto perps vs BTC (and with the STL shield)

Date: benchmark built 2026-11-01 (`47fa8ee`); first recorded run 2026-11-05 (Phase 1 working tree, with the 0030 universe fix)
Decisions: [0012](../decisions/0012-engine-24-7-generalisation.md)–[0014](../decisions/0014-crypto-benchmark-protocol.md), [0026](../decisions/0026-safety-thresholds.md), [0030](../decisions/0030-skip-market-wide-dump-holes.md)
Command: `uv run python download_crypto_data.py` (once, ~30 min, 266 MB), then `uv run python run_crypto_benchmark.py --bar 1d|4h|1h`
Raw: `results/crypto/{1d,4h,1h}_broad/` (metrics_{full,dev,holdout}.csv, stl_summary.csv, safety_monitor.csv, bootstrap_vs_btc.csv)

## History
The benchmark was run when it was built, but its results were never written down. On the first re-run it failed: a missing day in Binance's daily dump (2026-10-28, all symbols) emptied the universe. Fixed by [0030](../decisions/0030-skip-market-wide-dump-holes.md); the universe before that day is unchanged.

## Setup
Binance USD-M perps, point-in-time top-50 universe by 90-day median dollar volume (about 60 tradable symbols on a typical day), delisted symbols included, funding charged. `Config.for_tier` defaults, nothing fitted: 1d = 365-day lookback, 14-day rebalance; 4h = 120-day lookback, 5-day rebalance; 1h = 60-day lookback, 2-day rebalance; 7 bp costs. Dev period = everything before the final 12 months (ends 2025-11-03). Trading starts later on 1d (longer warmup), so the 1d dev window (2022-01 to 2025-11) is shorter than 4h/1h (2020 to 2025-11).

**Only the dev period is used for conclusions.** The holdout tables are in the raw files, unread for decisions.

## Results: dev period
| Bar | Strategy | CAGR | Vol | Sharpe | MaxDD |
|---|---|---|---|---|---|
| 1d | BTC | 32.6% | 52% | 0.80 | -67% |
| 1d | MAS | -16.2% | 57% | -0.03 | -64% |
| 1d | **MAS+STL** | 0.8% | **20%** | 0.14 | **-29%** |
| 1d | MAS-H | -8.9% | 47% | 0.04 | -55% |
| 1d | Naive avg | -12.0% | 37% | -0.16 | -51% |
| 4h | BTC | 55.6% | 60% | 1.04 | -77% |
| 4h | MAS | -8.9% | 74% | 0.25 | -88% |
| 4h | **MAS+STL** | 4.5% | **24%** | 0.31 | **-34%** |
| 4h | MAS-H | -3.6% | 63% | 0.26 | -82% |
| 4h | Naive avg | 2.1% | 52% | 0.30 | -67% |
| 1h | BTC | 56.8% | 60% | 1.05 | -77% |
| 1h | MAS | 17.8% | 80% | 0.61 | -85% |
| 1h | **MAS+STL** | 15.0% | **26%** | 0.67 | **-38%** |
| 1h | MAS-H | 16.0% | 68% | 0.56 | -77% |
| 1h | Naive avg | 10.7% | 58% | 0.47 | -74% |

Turnover per year and cost drag (CAGR lost to costs), full period:
| Bar | MAS | MAS+STL | MAS-H |
|---|---|---|---|
| 1d | 12.8 / 0.9% | 6.1 / 0.3% | 9.9 / 0.8% |
| 4h | 31.0 / 1.9% | 10.2 / 0.7% | 23.3 / 1.9% |
| 1h | 68.9 / 5.9% | 22.1 / 1.7% | 47.9 / 5.0% |

Paired block bootstrap, Sharpe(strategy) - Sharpe(BTC), full period: every MAS variant is below BTC on every bar size (1d -0.41, 4h -0.71, 1h -0.25 for MAS), but no interval excludes 0. Only equal-weight long-only is significantly worse than BTC.

## Results: STL specs, dev period (share of bars violated)
| Bar | System | phi_dd | phi_vol | phi_rec | phi_conc | Shield acted / rebalances | mean exposure |
|---|---|---|---|---|---|---|---|
| 1d | MAS | 80% | 66% | 57% | 0% | | |
| 1d | MAS+STL | 61% | 5% | 3% | 0% | 116 / 125 | 0.37 |
| 4h | MAS | 84% | 86% | 79% | 0.3% | | |
| 4h | MAS+STL | 64% | 15% | 9% | 0% | 444 / 450 | 0.29 |
| 1h | MAS | 81% | 90% | 84% | 0.6% | | |
| 1h | MAS+STL | 61% | 15% | 9% | 0% | 1158 / 1160 | 0.29 |

## Findings
1. **The v1 multi-agent system has no edge over BTC on crypto**, and on 1d and 4h it barely beats zero. With the long-short agents, the book holds about 60 volatile alts at gross 1 and runs at 57–80% vol, more than BTC itself. This is consistent with the team's move to a separate absolute-return engine (v2, decisions 0015–0020).
2. **The shield works on crypto as designed:** vol falls to 20–26% on every bar size, max drawdown roughly halves, cost drag falls by two-thirds (fewer and smaller trades), and the vol and recovery specs go from violated most of the time to 3–15%. Sharpe is equal or higher than plain MAS on all three bar sizes.
3. **The drawdown spec is violated on about 60% of bars even with the shield, and the shield sits mostly de-risked (exposure 0.29–0.37).** This points to the limits, not the shield. Decision 0026 gives crypto a 40% vol limit but keeps the stocks' 15% drawdown limit. For stocks the drawdown limit is 0.75x the vol limit; for crypto it is under 0.4x. This inconsistency is visible from the limits alone, without performance numbers. Changing it needs a new decision record ([0031, proposed](../decisions/0031-crypto-drawdown-limit.md)).
4. The 1h bar is the best for every MAS variant (dev Sharpe 0.56–0.67), but also the most cost-sensitive (5.9% a year cost drag without the shield).
5. The hierarchy (MAS-H) lowers vol and turnover a little but does not change the picture.
