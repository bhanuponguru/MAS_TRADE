# 001. Baseline: the multi-agent system on US stocks

Date: first run 2026-10-18 (initial commit `b48056d`); numbers below re-run   Decisions: [0001](../decisions/0001-us-stock-universe.md)–[0008](../decisions/0008-no-lookahead-invariant.md)
Command: `uv run python run_backtest.py`

Numbers re-run on 2026-11-05 (code `7eff0f1` + Phase 1 working tree with the shield off, which a test guarantees is identical to the pre-STL code). The original runs were never saved (`results/` is gitignored).

## Question
Does the consensus system (W-MSR F=1, K=10, pin 0.3, capital flow eta 0.5) beat its own agents and simple baselines?

## Setup
20 US large caps, trading 2017-01 to 2025-12 (2015–2016 = lookback + warmup), 21-day rebalance, 5 bp costs.

## Results (full period, sorted by Sharpe)
| Strategy | CAGR | Vol | Sharpe | MaxDD | Turnover /yr |
|---|---|---|---|---|---|
| EW long-only | 19.1% | 17.8% | 1.07 | -31.8% | 0.0 |
| ShrinkageMean (agent) | 17.3% | 18.5% | 0.96 | -30.7% | 2.2 |
| **Naive avg of agents** | 10.7% | 12.1% | **0.90** | -18.1% | 4.0 |
| Momentum (agent) | 16.0% | 19.2% | 0.87 | -32.6% | 4.1 |
| SPY | 15.1% | 18.5% | 0.85 | -33.7% | — |
| **MAS (W-MSR)** | 13.1% | 17.1% | **0.81** | -25.9% | 5.0 |
| AR1 | 11.7% | 15.8% | 0.78 | -24.8% | 10.6 |
| EWMATrend | 10.3% | 16.4% | 0.68 | -29.0% | 6.6 |
| LowVolTilt | 5.0% | 17.1% | 0.37 | -36.1% | 4.5 |
| MeanReversion | -1.2% | 15.7% | 0.00 | -42.6% | 17.2 |

Capital share per agent, first -> last day: Momentum 17.0 -> 17.4%, MeanReversion 14.2 -> 12.4%, ShrinkageMean 17.4 -> 19.8%, AR1 17.4 -> 20.0%, EWMATrend 17.4 -> 16.1%, LowVolTilt 16.6 -> 14.4%.

## Findings
1. MAS does **not** beat the naive average of the same agents (0.81 vs 0.90 Sharpe) and trades more (5.0 vs 4.0). The consensus and capital machinery adds turnover without adding return on this universe.
2. Long-only equal weight and SPY are hard to beat over a bull market. The long-short agents carry little market beta, so this comparison mostly measures beta.
3. Capital flows are slow and small: the worst agent (MeanReversion) still holds 12% at the end. eta 0.5 with trust in a narrow band moves little.
4. The system is a reasonable risk reducer: MaxDD -26% vs -31% to -43% for most single agents.

## Open questions this raised
Is the value of the MAS in resilience (experiment 003) rather than return? Would sharper trust (`trust_power`) or faster eta help? Neither has been tested.
