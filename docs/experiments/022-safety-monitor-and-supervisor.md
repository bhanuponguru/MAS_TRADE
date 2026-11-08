# 022. STL safety monitor and supervisor: the safety record, de-risking in drawdowns, and holding on an unsafe solve

Date: 2026-11-08   Decision: [0044](../decisions/0044-stl-safety-monitor-and-supervisor.md) (limits from [0026](../decisions/0026-safety-thresholds.md))   Code: `supervisor.py`, `engine.py`, `run_benchmark.py`
Proposal question: *Does an STL safety monitor with a supervisor keep the system inside its safety specifications in stress periods, and at what cost?*

## Question
(1) How do the system's STL specs (ex-ante volatility, drawdown, realised volatility with recovery, solver health) behave over the dev period and in the stress windows of May-July 2021, LUNA (May-July 2022) and FTX (November 2022-January 2023)? (2) Does the "derisk" supervisor reduce breaches of the drawdown spec? (3) Does the "hold" supervisor stop the system from trading on the corrupted solves of a misbehaving agent that the detector misses (experiment 021)?

## Rules (written and committed before any run)
Disclosure: the code was checked on the first 900 days of the 1d data (smoke test, carry + H2, hub; not logged as a trial): derisk acted (target down to 0.32), hold never triggered (worst relative residual 1e-6). No setting was changed after it; all limits come from decision 0026 (table in 0044).

**Part A, the main system** (carry + H2, hub, dev period) on 1d, 4h and 1h, safety "off" and "derisk"; on 1d also "hold". Seven runs.
- **A1 (gate, the monitor and the priced limits):** in every "off" run the solver-health spec holds at every rebalance (no unsafe solve, nothing held in the "hold" run), and the ex-ante volatility spec (<= 1.05 x target) holds at at least 95% of rebalances.
- **A2 (gate, derisk):** on each bar size, "derisk" has fewer bars violating the drawdown spec (365-day drawdown below -15%) than "off", and a shallower worst 365-day drawdown. If "off" never violates on a bar size, "derisk" must not violate either.
- **A3 (reported):** for every run and stress window: return, worst drawdown inside the window, volatility, lowest robustness of each spec, violating bars, lowest volatility multiplier; whole-period Sharpe, CAGR and maximum drawdown of "derisk" against "off" (the cost; no gate, 0036: limits are never chosen by Sharpe).

**Part B, a stealthy liar on real data** (1d, carry + H2 + reversal, graph complete with 1 gossip round, as experiment 019). `RankReversal` misbehaves from 2022-05-01 to 2022-07-31 only: it holds nothing and adds normal noise (standard deviation 0.01, new every iteration) to everything it sends. Runs: (a) no liar; (b) liar, no defence; (c) liar, safety "hold".
- **B1 (gate):** in (c) every rebalance whose solve is unsafe is held (trades nothing), every held rebalance is inside the liar's window, and no rebalance outside the window is unsafe; in (b) at least one rebalance inside the window trades on an unsafe solve (otherwise the attack did nothing and the test is void).
- **B2 (reported):** money and risk of (b) and (c) against (a): Sharpe, final equity, and return, worst drawdown and trading cost inside the window.

Expectation, stated up front: A1 passes; A2 passes on every bar size at a cost of a little return; the specs are tightest in May 2021 and LUNA; B1 passes; in (b) the corrupted solves trade a wrong portfolio inside the window, and (c) holds its positions through it.
