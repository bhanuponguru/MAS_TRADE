# 0022. Build the proposal's system on the v1 consensus engine; freeze v2

Status: **Accepted** (2026-11-05, approved by the user)   Date: 2026-11-05

## Context
The repo has two engines. v1 (`mas_trade/backtest.py`) has the parts the proposal is about: agent consensus (W-MSR, ADMM), trust, capital flow between agents, adversaries, communication graphs. v2 (`mas_trade/v2/`) is an absolute-return crypto engine (books, combiners, impact costs) that goes beyond the proposal. Building the safety layer, experiments and dashboard twice is not affordable.

## Options
1. **v1 only, v2 frozen**: v2 stays in the repo and its tests keep passing, but gets no new features.
2. Port everything to v2: more realistic costs, but loses the consensus/adversary story the proposal is graded on.
3. Both: double the work.

## Decision
Option 1. Demo universe: US stocks (20 large caps, 2015–2025) by default; crypto `majors` as a second dataset via `Config.for_tier`.

## Consequences
v2 results stay as a side finding (e.g. funding carry is the only net edge) and can be cited, but are not extended.

## Rollback
Nothing is deleted; un-freezing v2 is a matter of starting work on it again.
