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

**Amendment 1 (2026-11-09, after the runs; nothing in the rules changed).** (i) *A recording bug, fixed:* on a held rebalance the engine logged the ex-ante volatility of the rejected solve (about 54%) as the system's, instead of that of the positions it kept; the trades were right, only the monitor's record was wrong. Fixed in `engine.py` (the test of hold now checks the recorded volatility of held rebalances and fails on the old code); run (c) was re-run with the fix (label ends "rerun after monitor fix"; the first copy, same trades, is in the trial log once). Part A and runs (a), (b) never hold, so they are unaffected. (ii) *Run (b), the undefended noise liar, was stopped after 9 h 38 min without output.* A profile of its first attacked solve (2022-05-12) shows why: with the noise in the messages the iterates diverge (the largest value an agent steps on grows from 0.4 to 44 in 700 iterations) and each agent step's root finding slows from 0.02 s to 0.3 s, so one 3,000-iteration solve takes about 45 minutes, and the volatility search repeats it up to six times at each of the six attacked rebalances (`data/022/liar_solve_divergence.log`). Run (c) stops at the first unsafe solve, which is why it finished. Not in the trial log. For B1(b), runs (b) and (c) are identical up to 2022-05-12 (same data, same seeds, no hold before), and there the solve is unsafe (relative residual 1.32, limit 0.001) and diverging; with no supervisor (b) trades it. B2 for (b) is not measured.

Expectation, stated up front: A1 passes; A2 passes on every bar size at a cost of a little return; the specs are tightest in May 2021 and LUNA; B1 passes; in (b) the corrupted solves trade a wrong portfolio inside the window, and (c) holds its positions through it.

## Command
`results/022/runs.sh` (ten `run_benchmark.py` runs, tags `022_*`; part B (c) re-run by `results/022/rerun_hold.sh`, amendment 1). Tables: `data/022/runs.csv` (one row per run), `data/022/windows.csv` (the STL record per stress window), from the saved runs.

## Results, part A (carry + H2, hub, dev period)

| bar | safety | Sharpe | CAGR | worst 365-day drawdown | bars with drawdown below -15% | rebalances with ex-ante vol within 1.05 x target | worst ex-ante vol margin | unsafe solves | lowest vol multiplier |
|---|---|---|---|---|---|---|---|---|---|
| 1d | off | 1.394 | 31.2% | -23.7% | 211 | 97.8% | -0.5% | 0 | 1.0 |
| 1d | derisk | 1.277 | 23.9% | -19.7% | 229 | 100% | +0.4% | 0 | 0.2 |
| 1d | hold | 1.394 | 31.2% | -23.7% | 211 | 97.8% | -0.5% | 0 (nothing held) | 1.0 |
| 4h | off | 1.478 | 29.8% | -24.4% | 2,223 | 97.6% | -3.0% | 0 | 1.0 |
| 4h | derisk | 1.275 | 21.0% | -18.8% | 2,159 | 97.6% | -4.7% | 0 | 0.2 |
| 1h | off | 1.483 | 29.2% | -25.9% | 7,695 | **94.3%** | -10.0% | 0 | 1.0 |
| 1h | derisk | 1.462 | 24.3% | -16.7% | 5,135 | 94.3% | -10.0% | 0 | 0.2 |

(The vol margin is (limit - ex-ante vol) / limit with limit 1.05 x the target in force; a bar is one bar of the run's own size, so the drawdown counts are not comparable across bar sizes.)

- **A1: FAIL on 1h only.** The solver-health spec holds at every rebalance of every run (no unsafe solve; the 1d hold run held nothing; the few unconverged solves of 4h and 1h stopped below the 1e-3 residual). The ex-ante volatility spec holds at 97.8% (1d) and 97.6% (4h) of rebalances but at 94.3% on 1h (54 of 955), with breaches of up to 10% over the limit. Cause: the volatility price is found by at most five re-solves with a 2% band (engine), and on 1h the covariance moves faster between rebalances than the warm-started price follows. A limitation of the search, not a bug; reported as a failure.
- **A2: FAIL on 1d, PASS on 4h and 1h.** Derisk always makes the worst 365-day drawdown shallower (1d -19.7% against -23.7%; 4h -18.8% against -24.4%; 1h -16.7% against -25.9%), and on 4h and 1h it also cuts the bars below the -15% line (2,159 against 2,223; 5,135 against 7,695). On 1d it has *more* such bars (229 against 211): with smaller positions after the loss the account climbs back more slowly, so it stays below the line longer even though it never falls as far.
- **A3 (reported).** Cost of derisk: Sharpe -0.12 (1d), -0.20 (4h), -0.02 (1h); CAGR -7.3, -8.8, -4.9 points. In the stress windows (table `data/022/windows.csv`) the specs are tightest in **FTX** (Nov 2022 - Jan 2023), not May 2021 or LUNA as expected: it is the only window in which the drawdown spec is violated (1d 1 bar, 4h 444, 1h 1,741 bars, off). There derisk acts: on 4h the window's drawdown falls from -8.5% to -2.0% (volatility 20.8% to 6.7%), on 1h from -12.6% to -2.8%, at a lower return in the window (4h 8.2% to 3.7%). In May 2021 and LUNA the system made money (return 7-16%, drawdown in the window at most -8.5%) and derisk did not act. The realised-volatility spec with its 14-day recovery is violated only on 1d (34 bars off, 28 derisk; none in the windows).

## Results, part B (1d, carry + H2 + reversal, graph complete, 1 round; liar = reversal, noise 0.01, 2022-05-01 to 2022-07-31)
| run | Sharpe | final equity | CAGR | return in window | worst drawdown in window | trading cost in window | unsafe solves | held |
|---|---|---|---|---|---|---|---|---|
| (a) no liar | 1.257 | 3.56 | 25.9% | 11.7% | -3.0% | 0.86% | 8 (all in 2025, see below) | - |
| (b) liar, no defence | stopped (amendment 1) | - | - | - | - | - | first attacked solve: residual 1.32, diverging | - |
| (c) liar, hold | 1.033 | 2.77 | 20.3% | 6.7% | -5.8% | 0 | 15 | 15 |

- **B1: FAIL.** In (c) every unsafe solve is held (15 of 15, none traded), and all six rebalances inside the liar's window are held (relative residual 1.18-1.62 against the 1e-3 limit). But nine held rebalances are *outside* the window (2025-05-08 to 2025-10-23), with no liar: the decentralised solve stopped at the 3,000-iteration cap with a residual of 0.0013-0.0059. The same slow solves are in the clean run (a) (8 of them, which with no supervisor it traded). So the rule "nothing outside the window is unsafe" fails: the pre-fixed limit of 1e-3 cannot tell an attack (residual above 1) from slow honest convergence (around 0.003). The second half of B1 (in (b) at least one rebalance trades on an unsafe solve) holds by amendment 1 (ii).
- **B2 (reported).** Holding through the attack costs money here: inside the window (c) earns 6.7% against 11.7% for (a), with a deeper drawdown (-5.8% against -3.0%), because it keeps the pre-attack positions through the LUNA crash (their ex-ante volatility 12-15%, inside the limit). The larger cost is the false alarms: frozen for most of May-October 2025, the stale positions drifted to an ex-ante volatility of up to 31% (the volatility spec is violated at 5 held rebalances) and the whole-period Sharpe falls from 1.26 to 1.03. What (b) would have lost is not measured; its solve diverges (amendment 1).

## Findings
1. **The monitor works and is interpretable.** One record per bar of how far each spec is from violation shows where the system was in danger: the FTX collapse (Nov 2022 - Jan 2023) is the only stress window that breaks the drawdown spec, not May 2021 or LUNA as we expected.
2. **Derisk does what it is built for, with one failed gate.** The worst 365-day drawdown is shallower on every bar size (by 4-9 points) at a Sharpe cost of 0.02-0.20; on 4h and 1h the time spent below -15% also falls, on 1d it rises (slower recovery with smaller positions): A2 fails on 1d.
3. **The volatility limit is a price found by a short search, and on 1h it lags** (94.3% of rebalances within 1.05 x target against the 95% gate): A1 fails on 1h. A longer or better-started price search is the obvious fix, to be tested as its own variant.
4. **Hold stops a stealthy liar but, with its pre-fixed limit, also freezes the system on slow honest solves.** Every attacked solve was held; nine honest ones too, and the frozen positions cost more than the attack did. The residuals of the two cases differ by a factor of about 300, so a limit argued in advance between them (or more iterations before declaring a solve unsafe) is a follow-up experiment; it is not changed here.
5. **An undefended noise liar does not just bias the decentralised solve, it makes it diverge** (amendment 1), so in practice some supervisor is needed; detect-and-isolate (021) catches consistent liars, hold catches noisy ones.
6. A recording bug was found and fixed (amendment 1): the monitor must record what was held, not what was rejected.

Decision 0044: **Accepted** as a monitor and as optional supervisors, default off; derisk is usable (4h and 1h pass), hold needs the follow-up on its limit before it is switched on.
