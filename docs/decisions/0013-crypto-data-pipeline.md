# 0013. Crypto data: Binance USD-M, point-in-time and survivorship-free

Status: **Accepted**   Date: 2026-11-01   Commit: `47fa8ee`   Where: `mas_trade/crypto_data.py`, `download_crypto_data.py`

## Decision
- Klines and funding from Binance's public dump bucket, including delisted symbols (survivorship-free), cached as parquet in `data/crypto/`.
- Bars stamped with their **open** time; universe membership for bar t uses volume strictly before t's day.
- Universe: enter at rank <= top_n (50) by 90-day **median** daily dollar volume, stay while rank <= 1.5 * top_n (hysteresis), refreshed every 30 days.
- Excluded: stablecoin pairs, index contracts, gold tokens, TradFi perps. Holes <= 7 days are forward-filled inside a symbol's life.
- `majors` universe = top 20 with >= 365 days of history (stricter).

## Rationale (documented)
Median volume resists one-day spikes; hysteresis avoids churn at the boundary.

## Known limits (documented)
Manipulated high-volume small caps still get in, and a flat `cost_bps` understates their slippage (addressed in v2 by 0018).

## Rollback
`top_n`, universe choice.
