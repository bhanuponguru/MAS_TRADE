# 011. Data audit for the new system

Date: 2026-11-06   Decisions: [0013](../decisions/0013-crypto-data-pipeline.md), [0037](../decisions/0037-extended-data-store.md)
Code: branch `engine-rebuild` (`mas_trade/data.py`, `download_data.py`)
Command: `uv run python download_data.py --symbols BTCUSDT ETHUSDT SOLUSDT DOGEUSDT --bars 1d 1h --datasets klines funding premium spot metrics --root <scratch>` then `--coverage`

## Question
Which datasets does Binance's public bucket really provide, and is the funding mechanism the plan relies on right?

## Results
**Availability (bucket listing, 2026-11-06).**
| Dataset (USD-M futures unless noted) | Granularity | History |
|---|---|---|
| klines (OHLC, volume, trades, taker-buy volume) | monthly + daily | 2020-01 onward |
| premiumIndexKlines | monthly + daily, 1m / 1h / 8h ... | 2020-01 onward |
| markPriceKlines, indexPriceKlines | monthly + daily | 2020-01 onward |
| fundingRate | monthly | 2020-01 onward |
| metrics (open interest, long/short ratios, taker ratio) | **daily files only**, 5-minute rows | BTC 2020-09; SOL, DOGE 2021-12 |
| spot klines | monthly + daily | BTC 2017-08 onward |
| bookDepth, bookTicker, aggTrades, trades | daily / monthly | exist (not used yet) |
| liquidation snapshots | **absent** | none |

**Funding formula (BTCUSDT, 2024-06, 89 events, premium index 1-minute data).** funding = P + clamp(I - P, +-0.05%) with I = 0.01% per 8h and P the time-weighted average of the premium index over the 8-hour interval (weights 1..480 by minute):
| Premium average | mean abs error | max abs error | correlation with actual |
|---|---|---|---|
| time-weighted (weights 1..480) | 9.0e-7 | 1.1e-5 | 0.995 |
| equal-weighted | 3.4e-6 | 3.4e-5 | 0.936 |
Actual mean funding was 9.4e-5 per event, so the weighted formula's error is about 1% of the typical level. The formula is therefore usable as the mechanical funding model of the carry agent. With 1-hour premium bars the weighting must be approximated (hourly weight by position in the interval); its accuracy is to be measured when the agent is built.

**Funding intervals.** Over 4 symbols (28,751 events) one symbol (SOLUSDT) has 1.5% of events off the 8-hour grid with gaps as short as 2 hours: Binance shortens the interval at the funding cap. Event-time storage handles this (sums per bar are right); anything assuming fixed 8-hour events would not.

**Probe download (BTC, ETH, SOL, DOGE; 1d + 1h bars, premium 1h, spot 1h, funding, metrics).** All four symbols downloaded for every dataset, 54 MB in total. Metrics (hourly snapshots): open interest has no gaps; top-trader ratios are missing 14-18% of hours, the taker ratio 6-7%, the global long/short ratio about 1%; 11-44 hours are missing entirely per symbol. Consumers must handle NaN and must lag metrics by at least one bar (snapshots are stamped at their own time).

## Findings
1. Open interest, long/short and taker data exist only from late 2020 / late 2021 and only as daily files: about 1,800 requests per symbol (the full universe of about 240 symbols is roughly 430,000 requests). It stays opt-in (`--datasets metrics`).
2. Liquidation data is not publicly available: any liquidation-based agent is out of scope.
3. The plan's funding model is sound, with the weighting caveat above.
4. Crowding signals (open interest, long/short) can only be tested from 2021-12 for most symbols, a shorter sample than carry or momentum.
5. Deviation from the plan: the Phase 0 gate "old v2 tables reproduced from the extended store" cannot be met before the engine and agents exist; it moves to Phase 2 (legacy-equivalent carry agent). Phase 0 is gated on this coverage and interval audit instead.

## Not yet done
The full re-download of all universe symbols with the extended columns (klines for 1d/4h/1h, premium 1h, funding) has not been run; metrics and spot are opt-in.
