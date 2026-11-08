# 0044. STL safety monitor and supervisor of the system

Status: **Proposed (implementation; experiment 022 decides)**   Date: 2026-11-08   Where: `supervisor.py`, `engine.py`, `config.py` (`safety`, `dd_limit`, `dd_days`, `safety_buffer`, `safety_min_scale`, `hold_tol`, `faulty_window`, `attack_kind`), `cells_admm.py` / `graph_admm.py` (`state["rel_res"]`), `run_benchmark.py`   Evidence: `tests/test_supervisor.py`; experiment 022

## Context
The proposal promises an STL safety monitor and a supervisor. Decision 0036 placed STL specs at the inputs (belief sanity), the agents (calibration scaling the Kelly fraction) and the system (the volatility limit and beta band as PRICES inside the optimiser), and listed "reporting (robustness traces)", which was never built. Two gaps are left: (1) there is no record over time of whether the system's specs hold, so nobody can see the safety margin during a crash; (2) nothing reacts to a drawdown (the priced limits act on ex-ante risk, not on losses), and experiment 021 showed that a misbehaving agent who sends noise is not detected and makes the solver produce a wrong portfolio that does not converge.

## Options
1. **A post-hoc shield that scales the finished portfolio to cash** (the old v1 shield, 0025). Rejected before (0036): rescaling a cost-aware solution re-trades the whole book.
2. **More priced constraints** (a drawdown constraint inside the ADMM). A drawdown is a path property, not a function of the next portfolio; as a constraint it has no clean form.
3. **A monitor plus a supervisor that acts through what the optimiser already has** (chosen):
   - *Monitor* (reporting only): per bar, the STL robustness of the system specs, from the run's traces: phi_vol (ex-ante volatility at a rebalance <= 1.05 x the target in force), phi_dd (drawdown from the peak of the last 365 days >= -15%), phi_rvol (realised 30-day volatility <= 40%, and a breach recovered within 14 days: `stl.recovery`), phi_solve (the solve converged or its relative residual <= 1e-3). Saved per run as `safety.csv`, summarised for the stress windows May-July 2021, May-July 2022 (LUNA) and November 2022-January 2023 (FTX).
   - *Supervisor* "derisk": the volatility target is multiplied by `stl.kelly_scale` of the margin of phi_dd (1 while half the drawdown budget is left, falling linearly to 0.2 at the limit). It acts through the existing priced volatility limit, so it is not a post-hoc rescale: the optimiser re-solves with a tighter target, costs included. The drawdown uses only bars before the rebalance.
   - *Supervisor* "hold": a rebalance whose solve is unsafe (did not converge and relative residual above 1e-3) trades nothing; the drifted positions are kept. The fail-safe against a misbehaving agent that the detector misses.

## Limits and their mandate (written before any run)
All values come from the mandate of decision 0026 (approved by the user on 2026-11-05) and are not chosen by any backtest:
| Setting | Value | Mandate |
|---|---|---|
| `dd_limit`, `dd_days` | 15% over 365 days | 0026: lose at most about half of what the equity market lost in its worst stretch within any one year; the same horizon in calendar days for crypto. |
| `safety_buffer`, `safety_min_scale` | 0.5, 0.2 | 0026: start de-risking with half the drawdown budget left; never below 20% so the system keeps a track record to recover with. |
| phi_rvol | 40% over 30 days, recover within 14 days | 0026's crypto volatility ceiling and recovery horizon (twice the 20% target of 0036). |
| phi_vol | 1.05 x target | the priced limit's own search accepts 2%; 5% is a monitor tolerance, not a new limit. |
| `hold_tol` | 1e-3 relative residual | a portfolio off by 0.1% of its size is immaterial against one rebalance's fee (5 bp on the traded part); a solve worse than that is not a portfolio the agents agreed on. Clean hub solves reach 1e-6 (smoke test, first 900 days). |

## Decision
Option 3, behind `EngineConfig.safety = "off" | "derisk" | "hold" | "both"`, default "off" (no change to any earlier result); the monitor record is written by every `run_benchmark.py` run. A faulty agent can be limited to a window (`faulty_window`) and can send noise (`attack_kind = "noise"`), so the hold supervisor can be tested against the stealthy liar of experiment 021 on real data.

## Consequences
- The safety margin of every spec is visible bar by bar, including in the crash windows.
- "derisk" costs return when it acts (smaller positions after losses); its value is fewer and shallower breaches of the drawdown spec. It is judged on that, never on Sharpe (0036).
- "hold" can keep stale positions through a period of bad messages; it trades nothing rather than something wrong.

## Rollback
Leave `safety = "off"` (nothing changes) or delete `supervisor.py`, its fields and its tests; the monitor output files can be ignored.
