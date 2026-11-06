# 0001. Start on 20 US large caps, daily data from yfinance

Status: **Superseded by 0032** (was: Accepted)   Date: 2026-10-18   Commit: `b48056d`   Where: `config.TICKERS`, `mas_trade/data.py`

## Context
The proposal asks for a controlled historical simulation first.

## Decision
20 hand-picked US large caps over several sectors (AAPL ... VZ) and SPY as the benchmark. Daily adjusted closes from yfinance, 2015-01-01 to 2025-12-31, downloaded once and cached in `data/prices.csv`.

## Rationale (inferred)
Free data, liquid names, small enough for fast runs and readable plots.

## Known limits
The list is **today's** large caps, so it is survivorship-biased: it leaves out companies that failed or shrank. The bias makes long-only results look better, and it is one reason the crypto pipeline (0013) was built survivorship-free.

## Rollback
`Config.tickers`, `start`, `end`.
