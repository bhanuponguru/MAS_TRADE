# 0015. Start a second engine (v2) judged in absolute terms

Status: **Accepted (now frozen if 0022 is accepted)**   Date: 2026-11-01   Commit: `47fa8ee`   Where: `mas_trade/v2/`, `run_v2_benchmark.py`, `V2Config`

## Context
Comparing a long-short, gross-1 portfolio with BTC buy-and-hold mixes market exposure with skill.

## Decision
A separate engine whose question is "does it make money net of everything?": net Sharpe vs 0, and P&L split into market / selection / funding / cost. Three stages: books -> combiners -> execution. The v1 engine is untouched.

## Rationale
Documented: absolute terms, not against BTC. Inferred: the v1 framing could not separate beta from selection.

## Consequences
Two engines to maintain. 0022 proposes freezing v2.

## Rollback
v2 is self-contained; v1 does not import it.
