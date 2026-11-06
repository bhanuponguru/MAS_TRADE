import io
import zipfile

import numpy as np
import pandas as pd

from mas_trade import data as cd

KL_HEADER = "open_time,open,high,low,close,volume,close_time,quote_volume,count,tb,tbq,ignore\n"


def kline_csv(ts, close, qv, header=True):
    rows = "".join(f"{t},1,1,1,{c},1,{t},{q},1,1,1,0\n" for t, c, q in zip(ts, close, qv))
    return ((KL_HEADER if header else "") + rows).encode()


def test_parse_klines_header_noheader_and_microseconds():
    ms = [1704067200000, 1704153600000]
    a = cd.parse_klines(kline_csv(ms, [10.0, 11.0], [5.0, 6.0], header=True))
    b = cd.parse_klines(kline_csv(ms, [10.0, 11.0], [5.0, 6.0], header=False))
    c = cd.parse_klines(kline_csv([m * 1000 for m in ms], [10.0, 11.0], [5.0, 6.0]))  # microseconds
    for df in (a, b, c):
        assert list(df["close"]) == [10.0, 11.0] and list(df["quote_volume"]) == [5.0, 6.0]
        assert str(df.index.tz) == "UTC" and df.index[0] == pd.Timestamp("2024-01-01", tz="UTC")


def test_parse_funding_and_unzip_roundtrip():
    raw = b"calc_time,funding_interval_hours,last_funding_rate\n1704067200000,8,0.0003\n1704096000000,8,-0.0001\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", raw)
    f = cd.parse_funding(cd._unzip(buf.getvalue()))
    assert np.allclose(f["rate"], [0.0003, -0.0001]) and f.index[1] - f.index[0] == pd.Timedelta(hours=8)


def test_stable_pairs_flagged():
    assert cd.is_stable_pair("USDCUSDT") and cd.is_stable_pair("FDUSDUSDT") and not cd.is_stable_pair("BTCUSDT")


def _write(root, bar, sym, idx, close, qv=None):
    d = root / bar
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"close": close, "quote_volume": qv if qv is not None else 1.0}, index=idx).to_parquet(d / f"{sym}.parquet")


def synthetic_root(tmp_path, n_days=120, n_sym=6):
    root = tmp_path / "crypto"
    idx = pd.date_range("2022-01-01", periods=n_days, freq="D", tz="UTC")
    rng = np.random.default_rng(0)
    for k in range(n_sym):
        # symbol k has volume (k+1) * 1e6, so SYM5 is the biggest; SYM0 delists on day 100
        sl = slice(0, 100) if k == 0 else slice(0, n_days)
        i = idx[sl]
        _write(root, "1d", f"SYM{k}USDT", i, 100 * np.cumprod(1 + rng.normal(0, 0.01, len(i))), (k + 1) * 1e6)
    _write(root, "1d", "BTCUSDT", idx, 100 * np.cumprod(1 + rng.normal(0, 0.01, n_days)), 1e5)
    return root


def test_universe_is_point_in_time_top_n_with_delisting(tmp_path):
    root = synthetic_root(tmp_path)
    uni = cd.build_universe(root, top_n=3, window=30, refresh_days=30, stat="mean")
    assert not uni.iloc[:30].any().any()                       # no member without a full trailing window
    row = uni.loc["2022-03-15"]
    assert set(row[row].index) == {"SYM5USDT", "SYM4USDT", "SYM3USDT"}
    assert not uni.loc["2022-04-15", "SYM0USDT"]                # delisted on day 100: gone from the universe
    # membership on day D must not depend on day D's own volume (or later)
    qv = pd.read_parquet(root / "1d" / "SYM1USDT.parquet")
    qv.iloc[60:, 1] = 1e12
    qv.to_parquet(root / "1d" / "SYM1USDT.parquet")
    uni2 = cd.build_universe(root, top_n=3, window=30, refresh_days=1, stat="mean")
    assert uni2.loc["2022-03-02"].equals(uni.loc["2022-03-02"])  # day 60 itself still unchanged
    assert uni2.loc["2022-03-03", "SYM1USDT"]                    # but the next day it has moved in


def test_universe_hysteresis_and_refresh_period(tmp_path):
    root = tmp_path / "crypto"
    idx = pd.date_range("2022-01-01", periods=260, freq="D", tz="UTC")
    vol = {"AUSDT": np.full(260, 9e6), "BUSDT": np.full(260, 8e6), "CUSDT": np.full(260, 5e6),
           "DUSDT": np.full(260, 4e6), "EUSDT": np.full(260, 1e6)}
    vol["CUSDT"][100:] = 3e6      # C slips to rank 4 (outside top_n=3, inside buffer 4.5); D takes rank 3
    vol["CUSDT"][170:] = 1e5      # later C collapses below the buffer
    for s, v in vol.items():
        _write(root, "1d", s, idx, 100.0, v)
    uni = cd.build_universe(root, top_n=3, window=30, refresh_days=30, buffer=1.5)
    members = lambda d: set(uni.loc[d][uni.loc[d]].index)
    assert members("2022-03-15") == {"AUSDT", "BUSDT", "CUSDT"}
    assert members("2022-05-06") == {"AUSDT", "BUSDT", "CUSDT", "DUSDT"}   # D enters, C retained by the buffer
    assert members("2022-08-04") == {"AUSDT", "BUSDT", "DUSDT"}            # C finally fell out of the buffer
    flips = uni.astype(int).diff().abs().sum(axis=1)
    assert (flips[flips > 0].index.to_series().diff().dropna() >= pd.Timedelta(days=29)).all()  # only on refresh days


def test_exclusions_applied(tmp_path):
    root = synthetic_root(tmp_path)
    uni = cd.build_universe(root, top_n=3, window=30, exclude={"SYM5USDT"})
    assert "SYM5USDT" not in uni.columns


def test_panel_returns_eligibility_and_funding(tmp_path):
    root = synthetic_root(tmp_path)
    # 4h bars for two symbols, funding every 8h
    idx = pd.date_range("2022-01-01", periods=6 * 120, freq="4h", tz="UTC")
    for s in ("SYM5USDT", "BTCUSDT"):
        _write(root, "4h", s, idx, 100.0 * np.cumprod(np.full(len(idx), 1.001)))
        (root / "funding").mkdir(exist_ok=True)
        fi = pd.date_range("2022-01-01", periods=3 * 120, freq="8h", tz="UTC")
        pd.DataFrame({"rate": 0.0001}, index=fi).to_parquet(root / "funding" / f"{s}.parquet")
    rets, elig, fund, btc = cd.load_panel("4h", root, universe=cd.build_universe(root, top_n=3, window=30))
    assert list(rets.columns) == ["SYM5USDT"]                   # BTC has no volume rank here, so not a member
    assert np.allclose(rets["SYM5USDT"].dropna(), 0.001) and np.isnan(rets["SYM5USDT"].iloc[0])
    assert btc.name == "BTC" and np.allclose(btc.dropna(), 0.001)  # benchmark loads regardless of membership
    t0 = pd.Timestamp("2022-03-15 00:00", tz="UTC")
    assert elig.loc[t0, "SYM5USDT"] and elig.loc[t0 + pd.Timedelta(hours=20), "SYM5USDT"]
    assert not elig.loc["2022-01-10"].any().any()               # before a full trailing window
    # an 8h funding event lands in exactly one 4h bar; each pair of bars carries one 0.0001
    assert np.isclose(fund["SYM5USDT"].sum(), 0.0001 * 3 * 120)
    assert set(np.round(fund["SYM5USDT"].unique(), 8)) == {0.0, 0.0001}


def test_quality_report_flags_gaps_and_extremes():
    idx = pd.date_range("2022-01-01", periods=10, freq="D")
    r = pd.DataFrame({"A": [np.nan, 0.01, np.nan, 0.02, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0]}, index=idx)
    e = pd.DataFrame(True, index=idx, columns=["A"])
    q = cd.quality_report(r, e)
    assert q.loc["A", "gaps"] == 1 and q.loc["A", "extreme"] == 1 and q.loc["A", "bars"] == 8


def test_get_percent_encodes_non_ascii(monkeypatch):
    seen = {}

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"ok"

    monkeypatch.setattr(cd.urllib.request, "urlopen", lambda url, timeout: seen.setdefault("url", url) and R())
    assert cd._get("https://x/y?prefix=klines/龙虾USDT/1d/&marker=") == b"ok"
    assert seen["url"].isascii() and "%E9%BE%99" in seen["url"] and "&marker=" in seen["url"]


def test_short_gap_filled_inside_life_only(tmp_path):
    root = synthetic_root(tmp_path)
    idx = pd.date_range("2022-01-01", periods=60, freq="D", tz="UTC")
    close = pd.Series(100.0 * np.cumprod(np.full(60, 1.01)), index=idx)
    short_gap = close.drop(idx[20:23])                 # 3 missing days
    long_gap = close.drop(idx[20:32])                  # 12 missing days
    for sym, c in (("SYM5USDT", short_gap), ("SYM4USDT", long_gap)):
        _write(root, "1d", sym, c.index, c.values, 9e9)
    rets, *_ = cd.load_panel("1d", root, universe=cd.build_universe(root, top_n=3, window=10), max_gap_days=7)
    r = rets["SYM5USDT"]
    assert r.loc["2022-01-21":"2022-01-23"].isna().sum() == 0 and np.isclose(r.loc["2022-01-24"], 1.01 ** 4 - 1)
    assert np.isclose(r.loc["2022-01-21"], 0.0)        # carried, so no return invented inside the gap
    assert rets["SYM4USDT"].loc["2022-01-21":"2022-01-28"].notna().sum() == 7 and rets["SYM4USDT"].loc["2022-01-29":"2022-02-01"].isna().all()
    assert rets["SYM5USDT"].loc["2022-03-02":].isna().all()  # not extended past the symbol's last bar


def test_median_universe_ignores_one_day_volume_spike(tmp_path):
    root = tmp_path / "crypto"
    idx = pd.date_range("2022-01-01", periods=200, freq="D", tz="UTC")
    steady, pump = np.full(200, 5e6), np.full(200, 1e5)
    pump[150] = 5e9                                    # a single wash-traded day
    for s, v in (("AUSDT", np.full(200, 9e6)), ("BUSDT", steady), ("PUMPUSDT", pump)):
        _write(root, "1d", s, idx, 100.0, v)
    med = cd.build_universe(root, top_n=2, window=90, refresh_days=1, buffer=1.0, stat="median")
    mean = cd.build_universe(root, top_n=2, window=90, refresh_days=1, buffer=1.0, stat="mean")
    assert not med["PUMPUSDT"].any() and mean["PUMPUSDT"].any()


def test_market_wide_missing_day_does_not_empty_the_universe(tmp_path):
    root = synthetic_root(tmp_path)
    base = cd.build_universe(root, top_n=3, window=30, refresh_days=1, stat="median")
    for p in (root / "1d").glob("*.parquet"):              # the dump lacks one day for every symbol
        d = pd.read_parquet(p)
        d.drop(pd.Timestamp("2022-03-20", tz="UTC"), errors="ignore").to_parquet(p)
    uni = cd.build_universe(root, top_n=3, window=30, refresh_days=1, stat="median")
    assert uni.index.equals(base.index)                    # calendar keeps the hole day
    assert uni.loc["2022-03-20":].sum(axis=1).min() >= 3   # no 30-day blackout after the hole
    assert uni.loc["2022-03-20"].equals(uni.loc["2022-03-19"])   # hole day: previous members
    assert uni.loc[:"2022-03-19"].equals(base.loc[:"2022-03-19"])  # nothing before the hole changes
