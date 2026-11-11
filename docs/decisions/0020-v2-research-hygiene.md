# 0020. v2 research hygiene: sealed holdout, trial log, deflated Sharpe

Status: **Accepted**   Date: 2026-11-01   Commit: `3e2c17e`   Where: `v2/diagnostics.py`, `run_v2_benchmark.py --unseal`

## Decision
- The last 12 months are **sealed**: reported only with `--unseal`, and unsealing is logged. No full-period statistics in ad-hoc diagnostics.
- Every variant run is appended to `results/v2/trials.jsonl`.
- Deflated Sharpe (Bailey & Lopez de Prado) over all logged trials, to correct for how many variants were tried.

## Rationale (inferred)
Many combiners times bar sizes times universes is a multiple-testing problem.

## Note
`results/` is gitignored and the trial log is not on this machine, so the logged trials are not available here.
