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
Pending.
