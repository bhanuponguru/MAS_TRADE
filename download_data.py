"""Download Binance USD-M perp data into data/crypto/ (parquet cache).

python download_data.py [--bars 1d 4h 1h] [--top 50] [--datasets klines funding premium metrics spot]
                        [--symbols BTCUSDT ...] [--root DIR] [--refresh] [--workers 24] [--coverage]

1. daily klines for every USDT perp ever listed (incl. delisted), to rank by dollar volume
2. point-in-time top-N universe -> <root>/universe_<N>.csv
3. the requested datasets for every symbol that was ever in the universe (plus BTCUSDT), or for --symbols
   klines: perp OHLCV + taker volume per bar size; funding: events; premium: premium index 1h klines;
   metrics: open interest / long-short / taker ratios (one file per day per symbol: slow); spot: spot 1h klines
--coverage prints what is cached and the funding-interval audit, then exits.
"""
import argparse
from pathlib import Path

from mas_trade import data as cd

ap = argparse.ArgumentParser()
ap.add_argument("--bars", nargs="+", default=["1d", "4h", "1h"], choices=list(cd.FREQ))
ap.add_argument("--top", type=int, default=50)
ap.add_argument("--datasets", nargs="+", default=["klines", "funding", "premium"],
                choices=["klines", "funding", "premium", "metrics", "spot"])
ap.add_argument("--symbols", nargs="+", default=None, help="restrict step 3 to these symbols (probing / tests)")
ap.add_argument("--root", default=None, help="cache directory (default data/crypto)")
ap.add_argument("--refresh", action="store_true", help="re-download files that are already cached")
ap.add_argument("--workers", type=int, default=24)
ap.add_argument("--coverage", action="store_true")
args = ap.parse_args()
root = Path(args.root) if args.root else cd.crypto_dir()


def log(*a):
    print(*a, flush=True)


def summarise(res, what):
    bad = {s: r for s, r in res.items() if isinstance(r, Exception)}
    log(f"  {what}: {sum(r is True for r in res.values())} ok, "
        f"{sum(r is False for r in res.values())} no data, {len(bad)} errors")
    for s, e in list(bad.items())[:5]:
        log(f"    {s}: {e!r}")


if args.coverage:
    log(cd.coverage_report(root).to_string())
    fr = cd.funding_interval_report(root)
    if len(fr):
        log(f"\nfunding events: {int(fr.events.sum())} over {len(fr)} symbols; symbols with events off the 8h grid: "
            f"{int((fr.share_8h < 1).sum())} (shortest gap {fr.min_gap_h.min():.2f} h)")
    raise SystemExit(0)

if args.symbols:
    members = sorted(set(args.symbols))
else:
    symbols = cd.list_symbols()
    skip = cd.excluded_symbols() | {s for s in symbols if cd.is_stable_pair(s)}
    symbols = [s for s in symbols if s not in skip]
    log(f"{len(symbols)} candidate USDT perps (excluded {len(skip)} stable/index/TradFi/gold)")
    log("1/3 daily klines for ranking")
    summarise(cd.download_many(cd.download_klines, symbols, args.workers, root=root, interval="1d", refresh=args.refresh), "1d")
    uni = cd.build_universe(root, top_n=args.top, exclude=skip)
    members = sorted(set(uni.columns[uni.any()]) | {"BTCUSDT"})
    uni.to_csv(root / f"universe_{args.top}.csv")
    log(f"2/3 universe: {len(members)} symbols were ever in the top {args.top}; "
        f"{int(uni.sum(axis=1).median())} members on a typical day")

log(f"3/3 {', '.join(args.datasets)} for {len(members)} symbols")
kw = dict(root=root, refresh=args.refresh)
if "klines" in args.datasets:
    for bar in args.bars:
        summarise(cd.download_many(cd.download_klines, members, args.workers, interval=bar, **kw), bar)
if "premium" in args.datasets:
    summarise(cd.download_many(cd.download_klines, members, args.workers, interval="1h", kind="premium", **kw), "premium 1h")
if "spot" in args.datasets:
    summarise(cd.download_many(cd.download_klines, members, args.workers, interval="1h", kind="spot", **kw), "spot 1h")
if "funding" in args.datasets:
    summarise(cd.download_many(cd.download_funding, members, args.workers, **kw), "funding")
if "metrics" in args.datasets:
    summarise(cd.download_many(cd.download_metrics, members, args.workers, **kw), "metrics")
log("coverage:")
log(cd.coverage_report(root, set(members)).to_string())
