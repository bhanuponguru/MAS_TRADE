"""Binance USD-M perpetual data: klines and funding from the public dump bucket, cached as parquet.

Layout (under data/crypto/):  <interval>/<SYMBOL>.parquet   perp klines: open, high, low, close, volume, quote_volume, trades,
                                                            taker_buy_volume, taker_buy_quote_volume (UTC bar-open index)
                              premium/<interval>/<SYMBOL>.parquet   premium index klines (perp vs index; same columns)
                              spot/<interval>/<SYMBOL>.parquet      spot klines of the matching spot pair (keyed by the PERP symbol)
                              funding/<SYMBOL>.parquet       column rate (UTC settlement time index)
                              metrics/<SYMBOL>.parquet       hourly snapshots of open interest, long/short and taker ratios
Delisted symbols are in the bucket too, so the universe is survivorship-free.

Timing convention: a bar is stamped with its OPEN time; return[t] = close[t] / close[t-1] - 1 is earned
over bar t. Universe membership for bar t is decided from daily volume strictly before t's day.
Metrics are stamped with the time of the snapshot: a consumer deciding at bar open t must lag them by at least one bar.
"""
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
CDN = "https://data.binance.vision"
FAPI = "https://fapi.binance.com"
UM = "data/futures/um"
FREQ = {"1d": "1D", "4h": "4h", "1h": "1h", "15m": "15min", "5m": "5min"}
STABLE_BASES = {"USDC", "TUSD", "FDUSD", "BUSD", "USDP", "DAI", "USDE", "AEUR", "EUR", "USD1", "UST", "USDS"}
NOT_CRYPTO = {"BTCDOMUSDT", "DEFIUSDT", "PAXGUSDT", "XAUTUSDT"}  # index / gold-token contracts: Track B


def crypto_dir():
    return ROOT / "data" / "crypto"


# ------------------------------------------------------------------ http
def _get(url, retries=4):
    """Bytes of url, or None on 404. Non-ASCII symbol names (e.g. Chinese meme coins) are percent-encoded."""
    url = urllib.parse.quote(url, safe=":/?&=%")
    for k in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k == retries - 1:
                raise
        except Exception:
            if k == retries - 1:
                raise
    return None


def _list(prefix, delimiter=""):
    """All (keys, common prefixes) under a bucket prefix, following pagination."""
    keys, prefixes, marker = [], [], ""
    while True:
        url = f"{BUCKET}?prefix={prefix}&delimiter={delimiter}&marker={marker}"
        root = ElementTree.fromstring(_get(url))
        ns = root.tag.split("}")[0] + "}"
        ks = [e.text for e in root.iter(f"{ns}Key")]
        ps = [e.find(f"{ns}Prefix").text for e in root.iter(f"{ns}CommonPrefixes")]
        keys += ks
        prefixes += ps
        if root.find(f"{ns}IsTruncated").text != "true":
            return keys, prefixes
        nxt = root.find(f"{ns}NextMarker")
        marker = nxt.text if nxt is not None else (ks or ps)[-1]


def list_symbols():
    """Every USDT-quoted perpetual that ever had monthly klines (live and delisted)."""
    _, pre = _list(f"{UM}/monthly/klines/", "/")
    names = [p.rstrip("/").split("/")[-1] for p in pre]
    return sorted(s for s in names if s.endswith("USDT") and "_" not in s)


def excluded_symbols():
    """Not part of the crypto universe: stablecoin pairs, index/gold contracts, TradFi perps
    (those are Track B). Current TradFi/non-COIN contracts come from exchangeInfo."""
    out = set(NOT_CRYPTO)
    info = json.loads(_get(f"{FAPI}/fapi/v1/exchangeInfo"))
    for s in info["symbols"]:
        if s.get("contractType") == "TRADIFI_PERPETUAL" or s.get("underlyingType") not in (None, "COIN"):
            out.add(s["symbol"])
    return out


def is_stable_pair(symbol):
    return symbol.removesuffix("USDT") in STABLE_BASES


# ------------------------------------------------------------------ parsing
def _ms_index(col):
    v = pd.to_numeric(col)
    unit = "us" if v.iloc[0] > 1e14 else "ms"  # newer dumps may use microseconds
    return pd.to_datetime(v, unit=unit, utc=True)


KLINE_COLS = {1: "open", 2: "high", 3: "low", 4: "close", 5: "volume", 7: "quote_volume", 8: "trades",
              9: "taker_buy_volume", 10: "taker_buy_quote_volume"}
METRIC_COLS = {"sum_open_interest": "oi", "sum_open_interest_value": "oi_value",
               "count_toptrader_long_short_ratio": "ls_top_count", "sum_toptrader_long_short_ratio": "ls_top_sum",
               "count_long_short_ratio": "ls_global", "sum_taker_long_short_vol_ratio": "taker_ratio"}
# kind -> (bucket prefix, dataset folder, cache subfolder)
SERIES = {"klines": (UM, "klines", ""), "premium": (UM, "premiumIndexKlines", "premium"), "spot": ("data/spot", "klines", "spot")}


def parse_klines(csv_bytes):
    df = pd.read_csv(io.BytesIO(csv_bytes), header=None)
    if not str(df.iloc[0, 0]).lstrip("-").isdigit():  # some files carry a header row
        df = df.iloc[1:]
    out = pd.DataFrame({name: pd.to_numeric(df[i]).values for i, name in KLINE_COLS.items()},
                       index=_ms_index(df[0]).values)
    out.index = pd.DatetimeIndex(out.index, tz="UTC")
    return out


def parse_metrics(csv_bytes):
    """Daily metrics file (5-minute rows) -> the snapshots taken exactly on the hour."""
    df = pd.read_csv(io.BytesIO(csv_bytes))
    out = pd.DataFrame({new: pd.to_numeric(df[old]).values for old, new in METRIC_COLS.items()},
                       index=pd.DatetimeIndex(pd.to_datetime(df["create_time"]), tz="UTC"))
    return out[out.index.minute == 0]


def spot_symbol(perp):
    """Spot pair of a perpetual: the 1000x / 1000000x / 1M quoting of small-price coins is a perp-only convention."""
    return re.sub(r"^(1000000|1000|1M)", "", perp)


def parse_funding(csv_bytes):
    df = pd.read_csv(io.BytesIO(csv_bytes), header=None)
    if not str(df.iloc[0, 0]).lstrip("-").isdigit():
        df = df.iloc[1:]
    idx = pd.DatetimeIndex(_ms_index(df[0]).values, tz="UTC")
    return pd.DataFrame({"rate": pd.to_numeric(df[2]).values}, index=idx)


def _unzip(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        return z.read(z.namelist()[0])


def _fetch_all(urls, parse):
    parts = []
    for u in urls:
        blob = _get(u)
        if blob:
            parts.append(parse(_unzip(blob)))
    if not parts:
        return None
    df = pd.concat(parts)
    return df[~df.index.duplicated(keep="last")].sort_index()


# ------------------------------------------------------------------ download
def _month(key):
    return re.search(r"(\d{4}-\d{2})(?:-\d{2})?\.zip$", key).group(1)


def _day(key):
    return re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", key).group(1)


def download_klines(symbol, interval, root=None, refresh=False, start="2020-01", kind="klines"):
    """Monthly dumps, plus daily dumps for months after the last monthly one. kind: perp "klines", "premium" index
    klines or "spot" klines (cached under the PERP symbol). Returns True if cached."""
    base, name, sub = SERIES[kind]
    path = (root or crypto_dir()) / sub / interval / f"{symbol}.parquet"
    if path.exists() and not refresh:
        return True
    remote = spot_symbol(symbol) if kind == "spot" else symbol
    mk, _ = _list(f"{base}/monthly/{name}/{remote}/{interval}/")
    months = sorted(k for k in mk if k.endswith(".zip") and _month(k) >= start)
    dk, _ = _list(f"{base}/daily/{name}/{remote}/{interval}/")
    last = _month(months[-1]) if months else start
    days = sorted(k for k in dk if k.endswith(".zip") and _month(k) > last)
    df = _fetch_all([f"{CDN}/{k}" for k in months + days], parse_klines)
    if df is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return True


def download_metrics(symbol, root=None, refresh=False, start="2020-09-01"):
    """Daily metrics dumps (open interest, long/short and taker ratios) -> hourly snapshots. Tops up an existing cache
    with the days after its last row. Returns True if cached."""
    path = (root or crypto_dir()) / "metrics" / f"{symbol}.parquet"
    old = pd.read_parquet(path) if path.exists() and not refresh else None
    if old is not None and len(old):
        start = str((old.index[-1] + pd.Timedelta(days=1)).date())
    keys, _ = _list(f"{UM}/daily/metrics/{symbol}/")
    days = sorted(k for k in keys if k.endswith(".zip") and _day(k) >= start)
    new = _fetch_all([f"{CDN}/{k}" for k in days], parse_metrics)
    df = new if old is None else (old if new is None else pd.concat([old, new]))
    if df is None:
        return False
    df = df[~df.index.duplicated(keep="last")].sort_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return True


def _funding_tail(symbol, since_ms):
    rows, t = [], since_ms
    while True:
        blob = _get(f"{FAPI}/fapi/v1/fundingRate?symbol={symbol}&startTime={t}&limit=1000")
        r = json.loads(blob) if blob else []
        rows += r
        if len(r) < 1000:
            break
        t = r[-1]["fundingTime"] + 1
    if not rows:
        return None
    idx = pd.DatetimeIndex(pd.to_datetime([x["fundingTime"] for x in rows], unit="ms", utc=True))
    return pd.DataFrame({"rate": [float(x["fundingRate"]) for x in rows]}, index=idx)


def download_funding(symbol, root=None, refresh=False, start="2020-01"):
    path = (root or crypto_dir()) / "funding" / f"{symbol}.parquet"
    if path.exists() and not refresh:
        return True
    mk, _ = _list(f"{UM}/monthly/fundingRate/{symbol}/")
    months = sorted(k for k in mk if k.endswith(".zip") and _month(k) >= start)
    df = _fetch_all([f"{CDN}/{k}" for k in months], parse_funding)
    if df is not None and months:  # the current month is not in the monthly dumps: use the REST tail
        since = int(df.index[-1].timestamp() * 1000) + 1
        tail = None
        try:
            tail = _funding_tail(symbol, since)
        except Exception:
            pass
        if tail is not None:
            df = pd.concat([df, tail])
            df = df[~df.index.duplicated(keep="last")].sort_index()
    if df is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return True


def download_many(fn, symbols, workers=24, **kw):
    """Run fn(symbol, **kw) over symbols in a thread pool; returns {symbol: ok or exception}."""
    def run(s):
        try:
            return fn(s, **kw)
        except Exception as e:  # keep going, report at the end
            return e
    with ThreadPoolExecutor(workers) as ex:
        return dict(zip(symbols, ex.map(run, symbols)))


# ------------------------------------------------------------------ universe
def _read(root, interval, symbols, col):
    frames = {}
    for s in symbols:
        p = root / interval / f"{s}.parquet"
        if p.exists():
            frames[s] = pd.read_parquet(p, columns=[col])[col]
    return pd.DataFrame(frames)


def build_universe(root=None, top_n=50, window=90, exclude=(), refresh_days=30, buffer=1.5, stat="median", min_age=0):
    """Point-in-time universe from daily dollar volume, refreshed every `refresh_days` days.

    A symbol's score on day D is its median (stat="median", robust to one-day pump spikes) or mean
    quote volume over the `window` days BEFORE D; a full window of history is required, so very new
    listings are excluded. min_age: additionally require this many days of listing history. On each refresh day a symbol ENTERS at rank <= top_n and
    STAYS while rank <= buffer*top_n, so the universe holds top_n..buffer*top_n names and a name
    slipping a few places is not dropped and re-bought. Between refreshes the set only shrinks,
    when a symbol stops trading. Returns a boolean frame (days x symbols).

    A day on which NO symbol has a daily bar is a missing dump day (2026-10-28 is one), not a day on
    which everything stopped trading: it is left out of the volume windows and keeps the previous
    day's membership (decision 0030). Without this one such day empties the universe for `window` days."""
    root = root or crypto_dir()
    syms = sorted(p.stem for p in (root / "1d").glob("*.parquet"))
    syms = [s for s in syms if s not in set(exclude) and not is_stable_pair(s)]
    qv = _read(root, "1d", syms, "quote_volume")
    qv.index = qv.index.tz_localize(None)
    days = pd.date_range(qv.index.min().normalize(), qv.index.max().normalize(), freq="D")
    qv = qv.reindex(days)
    qv = qv.loc[qv.notna().any(axis=1)]                # drop market-wide dump holes (decision 0030)
    full = qv.notna().astype(float).rolling(window).sum().eq(window)
    if min_age:
        full &= qv.notna().cumsum().shift(1).fillna(0).ge(min_age)
    roll = qv.fillna(0).rolling(window)
    score = (roll.median() if stat == "median" else roll.mean()).where(full).shift(1)  # strictly before day D
    rank = score.rank(axis=1, ascending=False, method="first")
    out = pd.DataFrame(False, index=score.index, columns=score.columns)
    members, last = set(), None
    for i, day in enumerate(score.index):
        r = rank.iloc[i]
        if r.notna().any() and (last is None or (day - last).days >= refresh_days):
            members = {s for s in members if r[s] <= buffer * top_n} | set(r.index[r <= top_n])  # NaN rank: False
            last = day
        members = {s for s in members if score.iloc[i][s] == score.iloc[i][s]}  # still trading
        out.loc[day, list(members)] = True
    return out.reindex(days).ffill().fillna(False).astype(bool)   # a hole day keeps the day before's members


def load_universe(name="broad", root=None):
    """Named universes. broad: the top-50 files written by download_data.py.
    majors: top 20 by the same rule with at least 365 days of history (stricter, a robustness check
    against thinly-established or pumped small caps); built from the cached daily bars."""
    root = root or crypto_dir()
    broad = pd.read_csv(root / "universe_50.csv", index_col=0, parse_dates=True).astype(bool)
    if name == "broad":
        return broad
    if name == "majors":
        everything = {p.stem for p in (root / "1d").glob("*.parquet")}
        return build_universe(root, top_n=20, exclude=everything - set(broad.columns), min_age=365)
    raise ValueError(name)


# ------------------------------------------------------------------ panel
def load_panel(bar, root=None, top_n=50, start=None, end=None, universe=None, max_gap_days=7):
    """(returns, eligible, funding, btc) on a bar grid for every symbol that was ever in the universe.

    returns: per-bar close-to-close, NaN before listing, after delisting and in gaps longer than max_gap_days
    eligible: bar t -> symbol was in the top_n by trailing daily volume before t's day
    funding: per-bar funding rate paid by longs (events are put in the bar containing them)"""
    root = root or crypto_dir()
    uni = build_universe(root, top_n) if universe is None else universe
    syms = [s for s in uni.columns if uni[s].any() and (root / bar / f"{s}.parquet").exists()]
    close = _read(root, bar, syms, "close")
    grid = pd.date_range(close.index.min(), close.index.max(), freq=FREQ[bar], tz="UTC")
    close = close.reindex(grid)
    # short holes in the dumps (e.g. 2022-02-26..03-01 and 04-01..04-03 hit ~48 symbols): carry the last
    # close over the gap INSIDE the symbol's life, so the gap return lands on the first observed bar
    limit = int(max_gap_days * pd.Timedelta(days=1) / pd.Timedelta(FREQ[bar]))
    later_valid = close.notna()[::-1].cummax()[::-1]
    close = close.ffill(limit=limit).where(later_valid)
    if start or end:
        close = close.loc[start:end]
    rets = close.pct_change(fill_method=None)
    day = rets.index.normalize().tz_localize(None)
    elig = uni[syms].reindex(day).fillna(False).astype(bool)
    elig.index = rets.index
    fund = pd.DataFrame(0.0, index=rets.index, columns=syms)
    for s in syms:
        p = root / "funding" / f"{s}.parquet"
        if p.exists():
            f = pd.read_parquet(p)["rate"]
            f = f.groupby(f.index.floor(FREQ[bar])).sum().reindex(rets.index).fillna(0.0)
            fund[s] = f
    btc = None  # the benchmark is independent of the universe
    if (root / bar / "BTCUSDT.parquet").exists():
        bc = pd.read_parquet(root / bar / "BTCUSDT.parquet")["close"].reindex(grid)
        btc = bc.loc[start:end].pct_change(fill_method=None).reindex(rets.index).rename("BTC")
    return rets, elig, fund, btc


def quality_report(rets, elig, big=0.5):
    """Per-symbol sanity table: span, bars, gaps inside the span, extreme bars, bars in the universe."""
    rows = {}
    for s in rets:
        r = rets[s]
        live = r.first_valid_index(), r.last_valid_index()
        if live[0] is None:
            continue
        span = r.loc[live[0]:live[1]]
        rows[s] = {"first": live[0], "last": live[1], "bars": int(span.notna().sum()),
                   "gaps": int(span.isna().sum()), "extreme": int((span.abs() > big).sum()),
                   "in_universe": int(elig[s].sum())}
    return pd.DataFrame(rows).T


# ------------------------------------------------------------------ audits
def coverage_report(root=None, symbols=None):
    """Per dataset: how many symbols are cached and when their history starts and ends."""
    root = root or crypto_dir()
    layout = {"1d": root / "1d", "4h": root / "4h", "1h": root / "1h", "premium 1h": root / "premium" / "1h",
              "spot 1h": root / "spot" / "1h", "funding": root / "funding", "metrics": root / "metrics"}
    rows = {}
    for name, d in layout.items():
        firsts, lasts = [], []
        for p in sorted(d.glob("*.parquet")) if d.exists() else []:
            if symbols is not None and p.stem not in symbols:
                continue
            idx = pd.read_parquet(p).index
            firsts.append(idx.min())
            lasts.append(idx.max())
        if firsts:
            rows[name] = {"symbols": len(firsts), "first_median": pd.Series(firsts).median().date(),
                          "first_latest": max(firsts).date(), "last_min": min(lasts).date()}
        else:
            rows[name] = {"symbols": 0}
    return pd.DataFrame(rows).T


def funding_interval_report(root=None, symbols=None, tol_s=60):
    """Spacing of funding events per symbol: share on the 8-hour grid and the shortest spacing seen. Binance shortens
    the interval at the cap, so any code assuming fixed 8-hour events would be wrong for those symbols."""
    root = root or crypto_dir()
    rows = {}
    for p in sorted((root / "funding").glob("*.parquet")):
        if symbols is not None and p.stem not in symbols:
            continue
        gap = pd.read_parquet(p).index.to_series().diff().dt.total_seconds().dropna() / 3600
        if len(gap):
            rows[p.stem] = {"events": len(gap) + 1, "share_8h": float((abs(gap - 8) * 3600 < tol_s).mean()),
                            "min_gap_h": float(gap.min())}
    return pd.DataFrame(rows).T
