# Reference numbers from the legacy implementation

Small copies of result tables produced by the legacy v1 (consensus MAS) and v2 (books/combiners) code, kept so the new system can be checked against them without carrying that code. The code itself is at git tag `legacy-v1-v2` (commit `b24f70a`); check it out in a separate worktree to regenerate anything here.

| Folder | Source command (at the tag) | Contents |
|---|---|---|
| `stocks/` | `run_backtest.py`, `run_adversary_experiment.py [--hier]` | full-period stock metrics, adversary tables (experiments 001-004) |
| `v1_crypto/<bar>_broad/` | `run_crypto_benchmark.py --bar <bar>` | **dev-period** metrics, bootstrap vs BTC, yearly returns (experiment 005) |
| `v2/<bar>_broad[_smooth]/` | `run_v2_benchmark.py --bar <bar> [--smooth]` | dev-period absolute tables, IC, regimes, yearly returns, ADMM convergence (experiments 006-007) |
| `v2/trials.jsonl` | every v2 run | append-only trial log (used to deduplicate the trial count for the deflated Sharpe) |

The sealed-holdout tables (`metrics_holdout.csv`, `metrics_full.csv`) were deliberately NOT copied. v2 runs were dev-only (holdout sealed). Timestamps and exact numbers are as produced on 2026-11-05; the tables are the regression targets, not the code.
