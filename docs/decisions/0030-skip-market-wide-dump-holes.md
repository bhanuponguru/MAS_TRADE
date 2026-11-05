# 0030. Universe: a day missing for every symbol is a dump hole, not a market halt

Status: **Accepted** (2026-11-05; data-correctness fix needed to run the crypto benchmark)   Where: `crypto_data.build_universe`

## Context
Binance's daily kline dump has no bar on 2026-10-28 for any of the 651 symbols. The universe requires a gap-free 90-day volume window, so this one missing day emptied the universe for 90 days. The v1 crypto benchmark then stopped with "0 tradable assets at 2026-10-29" (the engine treats a universe collapse after trading has started as an error, see 0012). Prices did not show the problem because `load_panel` forward-fills short holes (0013).

## Options
1. **Drop days on which no symbol has a bar** from the volume windows; on such a day keep the previous day's members. Point-in-time is preserved: nothing after the day is used.
2. Cut the data before the hole: hides the problem and loses the most recent week.
3. Patch the missing day from the live REST API: an extra data source to maintain for one day.

## Decision
Option 1. Only days with **zero** symbols count as holes (the strictest rule), so a genuinely thin day is never skipped. There is exactly one such day in 2020-01 to 2026-11.

## Evidence
Rebuilding `universe_50.csv` with the fix leaves every day up to 2026-10-27 identical to the old file; the last week now has 59 members instead of 0. Test: `test_market_wide_missing_day_does_not_empty_the_universe`.

## Rollback
Remove the `qv.notna().any(axis=1)` filter and the final `reindex/ffill` in `build_universe`.
