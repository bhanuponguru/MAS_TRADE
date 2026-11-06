"""Download Binance USD-M perp data into data/crypto/ (parquet cache).

python download_data.py [--bars 1d 4h 1h] [--top 50] [--refresh] [--workers 24]

1. daily klines for every USDT perp ever listed (incl. delisted), to rank by dollar volume
2. point-in-time top-N universe -> data/crypto/universe_<N>.csv
3. requested bar sizes + funding for every symbol that was ever in the universe (plus BTCUSDT)
"""
import argparse
import sys

from mas_trade import data as cd

ap = argparse.ArgumentParser()
ap.add_argument("--bars", nargs="+", default=["1d", "4h", "1h"], choices=list(cd.FREQ))
ap.add_argument("--top", type=int, default=50)
ap.add_argument("--refresh", action="store_true", help="re-download files that are already cached")
ap.add_argument("--workers", type=int, default=24)
args = ap.parse_args()


def log(*a):
    print(*a, flush=True)


def summarise(res, what):
    bad = {s: r for s, r in res.items() if isinstance(r, Exception)}
    log(f"  {what}: {sum(r is True for r in res.values())} ok, "
        f"{sum(r is False for r in res.values())} no data, {len(bad)} errors")
    for s, e in list(bad.items())[:5]:
        log(f"    {s}: {e!r}")


symbols = cd.list_symbols()
skip = cd.excluded_symbols() | {s for s in symbols if cd.is_stable_pair(s)}
symbols = [s for s in symbols if s not in skip]
log(f"{len(symbols)} candidate USDT perps (excluded {len(skip)} stable/index/TradFi/gold)")

log("1/3 daily klines for ranking")
summarise(cd.download_many(cd.download_klines, symbols, args.workers, interval="1d", refresh=args.refresh), "1d")

uni = cd.build_universe(top_n=args.top, exclude=skip)
members = sorted(set(uni.columns[uni.any()]) | {"BTCUSDT"})
uni.to_csv(cd.crypto_dir() / f"universe_{args.top}.csv")
log(f"2/3 universe: {len(members)} symbols were ever in the top {args.top}; "
    f"{int(uni.sum(axis=1).median())} members on a typical day")

log("3/3 bars + funding for members")
for bar in args.bars:
    if bar != "1d":
        summarise(cd.download_many(cd.download_klines, members, args.workers, interval=bar, refresh=args.refresh), bar)
summarise(cd.download_many(cd.download_funding, members, args.workers, refresh=args.refresh), "funding")

log("quality (1d):")
rets, elig, fund, btc = cd.load_panel("1d", top_n=args.top)
q = cd.quality_report(rets, elig)
log(q.sort_values("in_universe", ascending=False).head(15).to_string())
log(f"symbols with gaps inside their span: {(q.gaps > 0).sum()}; with bars of |return| > 50%: {(q.extreme > 0).sum()}")
sys.exit(0)
