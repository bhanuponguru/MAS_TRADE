# 023. Final comparison on the dev period: one table for the proposal's questions, and the deflated Sharpe

Date: 2026-11-09   Decision: none (no design choice; this collects experiments 018-022)   Code: `final_table.py`
Proposal question: *Evaluation will consider both financial and multi-agent properties, including portfolio performance and risk, optimisation convergence, consensus behaviour, and adherence to the specified temporal safety requirements* (proposal, section 4), *with a centralised optimiser as the reference.*

## Question
(1) In one place: what does each part of the system (agents, the market of agents, the decentralised optimiser, topology, resilience mechanisms, safety supervisor) give in money, risk, convergence and communication, against the centralised reference? (2) Does the main system's Sharpe survive the correction for the number of variants tried (the deflated Sharpe, pending since experiment 013)?

## Rules (written and committed before the table is computed)
No new engine run and no new setting: `final_table.py` only reads the saved runs of experiments 018-022 (`results/<tag>/bars.csv`, `rebal.csv`, `safety.csv`, `run.log`) and `results/trials.jsonl`, on the dev period. The sealed final 12 months stay sealed.

**Tables (reported, no gate):**
- **T1 money and risk** per bar size (1d, 4h, 1h): carry alone, H2 alone, reversal alone, the market of two (the main system), the market of three, and the 50/50 fixed blend of carry and H2 (experiment 015's control): Sharpe with its 90% block-bootstrap interval (blocks of 7 days, 500 draws), CAGR, volatility, maximum drawdown, Calmar ratio, turnover.
- **T2 centralised against decentralised** (1d; experiments 019, 020): hub and every graph run: Sharpe, final equity against the hub, mean iterations per rebalance, rebalances that hit the iteration cap, messages per rebalance.
- **T3 resilience** (1d; experiments 021, 022 part B): each failure (link failures, offline agent, consistent liar with the detector, noise liar with no defence and with hold) against its correct reference: Sharpe, final equity, difference to the reference.
- **T4 safety** (all bar sizes; experiment 022): safety off, derisk and hold: bars violating each STL spec, worst robustness, worst 365-day drawdown, rebalances held, and the cost in Sharpe and CAGR.
- **T5 the deflated Sharpe** (Bailey and Lopez de Prado 2014, `diagnostics.deflated_sharpe`) of the main system (market of two, hub, safety off, experiment 018 runs) on each bar size.

**How trials are counted for T5 (fixed here, before computing):** a trial is one (strategy variant, bar size). The strategy variants on real data, from the experiment write-ups: carry in three calibrations (013), carry ladder rung 1 (014), H2 unrestricted and restricted (015a, 015b), market of two with each (015a, 015b), timed H2 (016, one trial with its market), reversal alone and market of three (017), and the re-runs after the volatility-limit fix of carry, H2, reversal, market of two, market of three (018): 15 variants on each of three bar sizes, **N_h = 45**. Engineering variants of the same strategies (consensus, topology, resilience, safety; 019-022) are reported separately as **N_all = N_h + the distinct names of 019-022 in the trial log** (the conservative count). The variance of the trial Sharpes is that of the annualised Sharpes of the 15 logged runs of experiment 018 (the only strategy trials whose numbers are all in the log), divided by the periods per year of the bar size; skewness, kurtosis and length are those of the main system's own returns. The curve of the deflated Sharpe against N from 1 to 200 is also reported.

**Gates:**
- **C1 (consistency):** every number that T1-T4 share with an earlier write-up (018-022) is reproduced to the rounding of that write-up (Sharpe to 0.001). Otherwise the table, not the experiment, is wrong, and is fixed before anything is reported.
- **C2 (the verdict on the main system):** the deflated Sharpe of the market of two is at least 0.95 at N_h on a bar size. Reported per bar size as PASS or FAIL; no rule is changed after seeing it.

Expectation, stated up front: C1 passes. C2 is uncertain and may fail: the logged trials range from Sharpe -1.2 (reversal) to 1.5, a wide spread that raises the bar the best trial must clear; with 5.5 years of data the main system's 1.4-1.5 may not clear it. A failure means the dev-period evidence alone does not establish the edge after multiple testing; it does not change the multi-agent results (T2-T4), which compare mechanisms on the same strategy.

## Command
`uv run python final_table.py` (writes `docs/experiments/data/023/`).

## Results
Tables: `data/023/T1_money.csv` ... `T5_curve.csv` (from `final_table.py`, saved runs only).

**C1 (consistency): PASS.** Every Sharpe shared with 018-022 is reproduced to 0.001.

**T1 money and risk** (net Sharpe with 90% block-bootstrap interval; dev period, all costs):

| | 1d | 4h | 1h |
|---|---|---|---|
| carry | 1.14 [0.36, 1.90] | 1.12 [0.36, 1.87] | 0.94 [0.25, 1.67] |
| H2 (BTC/ETH momentum) | 0.96 [0.24, 1.61] | 0.80 [0.08, 1.50] | 0.76 [-0.03, 1.44] |
| reversal | -0.66 [-1.29, -0.03] | -1.17 [-1.81, -0.48] | -0.99 [-1.63, -0.32] |
| **market of two (main system)** | **1.39 [0.61, 2.09]** | **1.48 [0.79, 2.15]** | **1.48 [0.76, 2.22]** |
| market of three | 1.26 [0.52, 1.97] | 1.34 [0.66, 2.01] | 1.33 [0.64, 2.03] |
| 50/50 blend carry + H2 | 1.45 [0.69, 2.13] | 1.36 [0.65, 2.08] | 1.20 [0.46, 1.88] |

Main system: CAGR 31.2% / 29.8% / 29.2%, volatility 21% / 19% / 18%, maximum drawdown -23.7% / -24.4% / -25.9%.

**T2 centralised against decentralised (1d).** Market of three: hub 1.258, graph complete 1.257, line 1.256, line with 3 rounds 1.257 (final equity within 0.3% of the hub). Eight agents: every topology within 0.002 Sharpe and 0.22% of the hub's final equity; mean iterations per rebalance 1,427 (hub) to 2,949 (line), messages 46,160 (ring, 1 round) to 123,854 (line); rebalances at the 3,000-iteration cap 27 (hub) to 122 (line). A 200-iteration budget costs 2.8% (hub) and 3.5% (ring) of final equity.

**T3 resilience (1d), each against its correct reference:** 30% link failures 1.239 / 1.239 against 1.240; the largest agent offline through LUNA 1.225 against 1.225; constant liar with the detector 1.182 against 1.182 (liar isolated); every case within 0.1% of the reference's final equity. Noise liar: no defence not measured (022, amendment 1); with hold 1.033 against 1.257 (-22% final equity, mostly from false alarms in 2025).

**T4 safety:** as in experiment 022 (derisk: worst 365-day drawdown -19.7% / -18.8% / -16.7% against -23.7% / -24.4% / -25.9%, Sharpe -0.12 / -0.20 / -0.02).

**T5 the deflated Sharpe of the main system. C2: FAIL on every bar size.**

| bar | Sharpe | skewness | kurtosis | DSR at N_h = 45 | DSR at N_all = 74 |
|---|---|---|---|---|---|
| 1d | 1.39 | 0.09 | 11.0 | 0.070 | 0.031 |
| 4h | 1.48 | 0.13 | 11.7 | 0.100 | 0.046 |
| 1h | 1.48 | 0.62 | 29.4 | 0.101 | 0.047 |

The variance of the trial Sharpes is 0.82 (annual; the 15 strategy runs of 018, from -1.17 to 1.48). The deflated Sharpe stays above 0.95 only up to N = 2 trials (0.98-0.99), and is 0.47-0.55 at N = 10 (`T5_curve.csv`).

## Findings
1. **The multi-agent mechanisms reproduce the central reference.** Decentralised consensus, every topology, link failures, an offline agent and an isolated liar all give the hub's portfolio to within 0.002 Sharpe; what they cost is communication (up to 2.7 times the messages and 4.5 times the capped rebalances on a line).
2. **The money result does not survive multiple testing on the dev period alone.** With 45 strategy trials of widely spread quality, the main system's Sharpe of about 1.4-1.5 is what the best of that many tries would show by chance with probability about 90%. This is a statement about the evidence, not that the system has no edge: carry's interval is above zero on every bar size, and the sealed final year (never seen) is the independent test the deflated Sharpe cannot replace.
3. **The market's value is protection, not return:** with good agents it equals a fixed blend (015); with a losing agent in the roster it cuts the loser's capital (018).
4. **Safety costs return and partly works** (022): derisk makes drawdowns shallower at a Sharpe cost of 0.02-0.20; hold needs a better-argued limit.
5. The proposal's trade-offs, in one line: decentralisation and resilience cost messages, safety costs return, the market of agents buys protection from a bad agent.
