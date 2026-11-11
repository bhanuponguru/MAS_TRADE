# 006. v2 engine: which agents and combiners have a net edge?

Date: 2026-11-01 (`3e2c17e`)   Decisions: [0015](../decisions/0015-v2-absolute-return-engine.md)–[0020](../decisions/0020-v2-research-hygiene.md)
Command: `uv run python run_v2_benchmark.py --bar 1d|4h|1h --universe broad [--smooth]`

## Status
Findings copied from the README (written at the time). Exact tables were not saved and the trial log (`results/v2/trials.jsonl`) is not on this machine. Dev period only: the holdout was never unsealed.

## Findings (net of fees, impact and funding, dev period)
1. Only two agents show a net edge: **funding carry** (Sharpe ~1.0–1.1 on all three bar sizes) and **BTC timing** (~0.85, mostly long-BTC beta).
2. Residual reversal has a positive rank-IC but **loses money** after costs: a signal can be real and still not tradable.
3. **No combiner beats inverse-vol** (EW, Fixed-Share Hedge, risk budgeting, Hedge+RB, C3 view fusion).
4. Deflated Sharpe over all logged trials is not significant for any row: after counting how many variants were tried, nothing is distinguishable from luck.
5. Zero-volume assets once produced 300% impact costs, which led to the `min_adv` floor ([0018](../decisions/0018-v2-costs-and-min-adv.md)).
