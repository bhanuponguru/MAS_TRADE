from dataclasses import replace

import numpy as np
import pandas as pd

from mas_trade.agents import Agent, default_agents
from mas_trade.backtest import run_backtest
from mas_trade.config import Config
from mas_trade.metrics import perf_stats

from test_backtest import CFG, make_returns


def gappy(n=700, N=8):
    """S6 starts trading at bar 300 (listing), S7 stops at bar 500 (delisting)."""
    r = make_returns(n, N)
    r.iloc[:300, 6] = np.nan
    r.iloc[500:, 7] = np.nan
    return r


class Always(Agent):
    def __init__(self, sign):
        self.name, self.sign = f"Always{sign:+d}", sign

    def forecast(self, window):
        return np.full(window.shape[1], float(self.sign))


def test_perf_stats_annualisation():
    r = pd.Series(np.random.default_rng(0).normal(0.001, 0.01, 1000))
    a, b = perf_stats(r, 252), perf_stats(r, 365)
    assert np.isclose(b["Vol"] / a["Vol"], np.sqrt(365 / 252))
    assert np.isclose(b["Sharpe"] / a["Sharpe"], np.sqrt(365 / 252))
    assert np.isclose(perf_stats(r)["Vol"], a["Vol"])  # default stays 252


def test_default_agents_scale_windows():
    base, big = default_agents(), default_agents(2.0)
    assert (base[0].skip, base[1].n, base[4].halflife) == (21, 5, 63)
    assert (big[0].skip, big[1].n, big[4].halflife) == (42, 10, 126)


def test_for_tier_converts_time_units_to_bars():
    d, h = Config.for_tier("1d"), Config.for_tier("1h")
    assert (d.periods_per_year, d.lookback, d.rebalance_days) == (365.0, 365, 14)
    assert (h.periods_per_year, h.lookback, h.rebalance_days) == (365.0 * 24, 1440, 48)
    assert Config.for_tier("1h", cost_bps=1.0).cost_bps == 1.0


def _check_mask(res, rets):
    idx = rets.index
    for d in res.weights.index:
        t = idx.get_loc(d)
        if t < 360:
            assert res.weights.loc[d, "S6"] == 0.0           # listed too recently for a full window
        if t >= 501:
            assert res.weights.loc[d, "S7"] == 0.0           # delisted: gap inside the window
    assert (res.weights.abs().sum(axis=1) <= 1 + 1e-9).all()
    assert np.isfinite(res.returns["MAS"]).all()


def test_listing_and_delisting_flat():
    rets = gappy()
    _check_mask(run_backtest(rets, CFG, default_agents()), rets)


def test_listing_and_delisting_hierarchical_budgets_follow_mask():
    rets = gappy()
    res = run_backtest(rets, replace(CFG, hierarchical=True, eta_sub="auto", cost_bps=0.0), default_agents())
    _check_mask(res, rets)
    for d, G in res.sub_capital.items():
        t = rets.index.get_loc(d)
        if t < 360:
            assert (G[:, 6] == 0).all()
        if t >= 501:
            assert (G[:, 7] == 0).all()
        assert (G >= 0).all()
    caps = res.capital.sum(axis=1)
    assert np.allclose(caps.values, 1e6 * (1 + res.returns["MAS"]).cumprod().values, rtol=1e-9)


def test_eligible_frame_blocks_assets():
    rets = make_returns()
    el = pd.DataFrame(True, index=rets.index, columns=rets.columns)
    el.iloc[400:, 0] = False
    res = run_backtest(rets, CFG, default_agents(), eligible=el)
    late = [d for d in res.weights.index if rets.index.get_loc(d) >= 400]
    assert late and (res.weights.loc[late, "S0"] == 0).all()
    assert (res.weights.drop(columns="S0").loc[late].abs().sum(axis=1) > 0).all()


def test_masked_no_lookahead():
    rets, cut = gappy(), 450
    alt = rets.copy()
    alt.iloc[cut:] = np.random.default_rng(9).normal(0.0, 0.05, alt.iloc[cut:].shape)
    for c in (CFG, replace(CFG, hierarchical=True)):
        a, b = run_backtest(rets, c, default_agents()), run_backtest(alt, c, default_agents())
        dates = [d for d in a.weights.index if rets.index.get_loc(d) <= cut]
        assert len(dates) > 10 and np.allclose(a.weights.loc[dates], b.weights.loc[dates])


def test_funding_charged_to_longs_paid_to_shorts():
    rets = make_returns(400, 6) * 0.0
    f = pd.DataFrame(0.001, index=rets.index, columns=rets.columns)
    cfg = replace(CFG, cost_bps=0.0, F=0)
    long = run_backtest(rets, cfg, [Always(+1)], funding=f).returns["MAS"]
    short = run_backtest(rets, cfg, [Always(-1)], funding=f).returns["MAS"]
    assert np.allclose(long, -0.001) and np.allclose(short, +0.001)
    assert np.allclose(run_backtest(rets, cfg, [Always(+1)]).returns["MAS"], 0.0)


# ---- metrics used by the crypto benchmark
def test_sortino_calmar_and_paired_bootstrap():
    from mas_trade.metrics import block_bootstrap_sharpe, extended_stats, split_holdout, yearly_returns
    rng = np.random.default_rng(0)
    idx = pd.date_range("2021-01-01", periods=1500, freq="D")
    r = pd.Series(rng.normal(0.001, 0.01, 1500), index=idx)
    e = extended_stats(r, 365)
    assert np.isclose(e["Sortino"], r.mean() * 365 / (np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(365)))
    assert np.isclose(e["Calmar"], e["CAGR"] / abs(e["MaxDD"]))
    pt, lo, hi = block_bootstrap_sharpe(r, 365, block=7, n_boot=400, seed=1)
    assert lo < pt < hi and np.isclose(pt, e["Sharpe"])  # same definition as perf_stats
    # a series against itself: the paired difference is exactly 0 with no spread
    assert block_bootstrap_sharpe(r, 365, 7, ref=r, n_boot=200) == (0.0, 0.0, 0.0)
    # a clearly better series has a paired CI above 0
    better = r + 0.003
    d, lo, hi = block_bootstrap_sharpe(better, 365, 7, ref=r, n_boot=400)
    assert d > 0 and lo > 0
    dev, hold = split_holdout(r.to_frame("a"), 12)
    assert len(dev) + len(hold) == len(r) and hold.index[0] >= r.index[-1] - pd.DateOffset(months=12)
    assert list(yearly_returns(r.to_frame("a")).index) == [2021, 2022, 2023, 2024, 2025]


def test_min_age_keeps_new_listings_out(tmp_path):
    from mas_trade import crypto_data as cd
    root = tmp_path / "crypto"
    idx = pd.date_range("2022-01-01", periods=300, freq="D", tz="UTC")
    for s, start in (("AUSDT", 0), ("BUSDT", 0), ("NEWUSDT", 150)):
        d = root / "1d"; d.mkdir(parents=True, exist_ok=True)
        i = idx[start:]
        pd.DataFrame({"close": 1.0, "quote_volume": 9e9 if s == "NEWUSDT" else 5e6}, index=i).to_parquet(d / f"{s}.parquet")
    plain = cd.build_universe(root, top_n=2, window=10, buffer=1.0, refresh_days=1)
    aged = cd.build_universe(root, top_n=2, window=10, buffer=1.0, refresh_days=1, min_age=120)
    assert plain.loc["2022-06-15", "NEWUSDT"]                       # day 165: 15 days old, big volume -> member
    assert not aged.loc["2022-06-15", "NEWUSDT"] and aged.loc["2022-10-15", "NEWUSDT"]  # in once 120 days old


def test_trading_starts_only_after_assets_available_plus_warmup():
    rets = make_returns(900, 8)
    el = pd.DataFrame(True, index=rets.index, columns=rets.columns)
    el.iloc[:400] = False                          # nothing tradable for the first 400 bars
    res = run_backtest(rets, CFG, default_agents(), eligible=el)
    first = rets.index.get_loc(res.returns.index[0])
    assert first >= 400 + CFG.warmup - CFG.rebalance_days   # warmup counted from availability, not from bar 0
    assert np.isfinite(res.returns["MAS"]).all() and (res.weights.abs().sum(axis=1) <= 1 + 1e-9).all()


def test_universe_collapse_after_trading_started_is_an_error():
    import pytest
    rets = make_returns(900, 8)
    el = pd.DataFrame(True, index=rets.index, columns=rets.columns)
    el.iloc[700:] = False
    with pytest.raises(ValueError, match="tradable"):
        run_backtest(rets, CFG, default_agents(), eligible=el)


def test_auto_eta_zero_variance_and_zero_cost_is_finite():
    from mas_trade.hierarchy import auto_eta
    e = auto_eta(np.array([0.0, 1e-4, 4e-4]), 21, 3.0, 0.0)       # free trading and a frozen price
    assert np.isfinite(e).all() and np.allclose(e, 1.0)
    e = auto_eta(np.array([0.0, 1e-4]), 21, 3.0, 5.0)
    assert e[0] == 0.0 and 0 < e[1] < 1                            # frozen price but costly trades: stay put
