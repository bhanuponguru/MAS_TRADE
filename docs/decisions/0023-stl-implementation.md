# 0023. Hand-written quantitative STL, robustness normalised by each limit

Status: **Accepted**   Date: 2026-11-05   Where: `mas_trade/safety.py`

## Context
The proposal's safety layer needs Signal Temporal Logic specs on portfolio risk, with a measure of how close the system is to a violation, not just yes/no.

## Options
1. **Write the operators by hand** (~60 lines): `always`/`eventually` (future-time, for scoring a finished run), `historically`/`once` (past-time, usable online), `and`/`or`/`not`/`implies`, predicates. Quantitative (robustness) semantics: robustness > 0 means satisfied, its size is the margin.
2. Use a library (`rtamt`, `stlpy`): full STL parser, but an extra dependency, a black box for the report, and more than we need.

## Decision
Option 1: it stays traceable to the lecture-style math, is fully unit-tested against brute force, and has no new dependency.
Robustness is **normalised by each spec's limit** (`le(x, c) = (c - x)/|c|`), so a value of 0.5 means "half the limit left" and different specs can be compared and combined with min/max.
Finite traces are truncated: a window running past the end uses what exists (for `eventually` this is pessimistic).

## Specs (in `safety.py` docstring)
phi_dd rolling drawdown, phi_vol rolling vol, phi_rec `G(vol > max -> F[0,R] vol <= max)`, phi_conc per-asset cap and gross, phi_cons consensus disagreement (monitor only).

## Rollback
Swapping in a library only touches the operator functions; specs and the shield call them by name.
