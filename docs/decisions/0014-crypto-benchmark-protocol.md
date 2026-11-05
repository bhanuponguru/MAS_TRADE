# 0014. v1 crypto benchmark protocol

Status: **Accepted**   Date: 2026-11-01   Commit: `47fa8ee`   Where: `run_crypto_benchmark.py`, `metrics.py`

## Decision
One walk-forward run per bar size with `Config.for_tier` defaults (nothing fitted). Reported as dev period vs final 12-month holdout: Sharpe, Sortino, Calmar, MaxDD, turnover, gross-vs-net cost drag, per-year returns. Plus a **paired moving-block bootstrap** of Sharpe(strategy) - Sharpe(BTC). Rule: do not tune settings by looking at the holdout.

## Evidence
[Experiment 005](../experiments/005-v1-crypto-benchmark.md): results were not written down; re-running needs the crypto download.

## Rollback
n/a (evaluation only).
