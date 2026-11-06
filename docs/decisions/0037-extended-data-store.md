# 0037. Extended data store

Status: **Accepted**   Date: 2026-11-06   Where: `mas_trade/data.py`, `download_data.py`   Evidence: [exp 011](../experiments/011-data-audit.md)

## Context
The stored bars held only close and quote volume. The agents in [0034](0034-hypothesis-roster-and-timing.md) need tail risk (high/low), the funding mechanism (premium index), crowding (open interest, long/short, taker flow) and a spot leg for basis.

## Decision
- Perp klines keep every column (open, high, low, close, volume, quote volume, trades, taker-buy volume). Premium index klines (1h), spot klines (1h, matched to the perp by symbol with the 1000x / 1M quoting stripped) and hourly on-the-hour snapshots of the metrics files are added, each as its own dataset folder.
- Metrics are stamped with their snapshot time and must be lagged by at least one bar by consumers (point-in-time rule). They are opt-in because they need one file per day per symbol.
- Audits are code, not a one-off: `coverage_report` and `funding_interval_report` (`download_data.py --coverage`).
- Existing caches hold only close and quote volume; a refresh run is needed to populate the new columns.

## Consequences
The full re-download takes longer and needs more disk. The OI / long-short history is short (2020-09 / 2021-12), which limits tests of crowding signals.

## Rollback
Datasets are independent folders; unused ones can be deleted without affecting the rest.
