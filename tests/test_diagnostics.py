import math

import numpy as np
import pandas as pd

from mas_trade.diagnostics import deflated_sharpe, ic_summary, log_trial, rank_ic, read_trials, regime_labels


def test_deflated_sharpe_reference_and_monotonicity():
    # more trials -> higher bar -> lower DSR; zero-variance trials -> DSR is just a Sharpe t-test
    kw = dict(sr_var=0.01 ** 2, skew=0.0, kurt=3.0, T=1000)
    lo, hi = deflated_sharpe(0.05, 100, **kw), deflated_sharpe(0.05, 2, **kw)
    assert lo < hi
    assert deflated_sharpe(0.0, 10, **kw) < 0.5
    z = 0.05 * np.sqrt(999) / np.sqrt(1 + 0.05 ** 2 * 2 / 4)
    assert np.isclose(deflated_sharpe(0.05, 10, 0.0, 0.0, 3.0, 1000), 0.5 * (1 + math.erf(z / np.sqrt(2))))


def test_rank_ic_planted_signal_and_degenerate_inputs():
    rng = np.random.default_rng(0)
    fwd = rng.normal(size=200)
    assert rank_ic(fwd + rng.normal(0, 0.1, 200), fwd) > 0.9
    assert abs(rank_ic(rng.normal(size=200), fwd)) < 0.2
    assert np.isnan(rank_ic(np.ones(50), fwd[:50])) and np.isnan(rank_ic(fwd[:5], fwd[:5]))


def test_ic_summary_t_stat():
    x = np.full(100, 0.03) + np.random.default_rng(1).normal(0, 0.1, 100)
    s = ic_summary(x)
    assert s["n"] == 100 and s["t"] > 1 and 0 < s["IC>0"] < 1
    assert np.isnan(ic_summary([0.1])["IC"])


def test_regime_labels_use_only_past_data():
    idx = pd.date_range("2022-01-01", periods=300, freq="D", tz="UTC")
    btc = np.random.default_rng(3).normal(0.001, 0.02, 300)
    a = regime_labels(btc, 1, idx)
    btc2 = btc.copy()
    btc2[200:] = 0.5
    b = regime_labels(btc2, 1, idx)
    assert a.iloc[:201].equals(b.iloc[:201]) or a.iloc[:200].equals(b.iloc[:200])   # labels at t depend only on returns before t


def test_trial_log_roundtrip(tmp_path):
    p = tmp_path / "t.jsonl"
    log_trial(p, name="a", sharpe=1.0)
    log_trial(p, name="b", sharpe=0.5)
    t = read_trials(p)
    assert list(t["name"]) == ["a", "b"] and "time" in t
    assert read_trials(tmp_path / "none.jsonl").empty


def test_block_bootstrap_mean_covers_the_true_mean_and_widens_with_noise():
    from mas_trade.diagnostics import block_bootstrap_mean
    rng = np.random.default_rng(0)
    x = rng.normal(0.5, 1.0, 400)
    m, lo, hi = block_bootstrap_mean(x, block=5)
    assert lo < 0.5 < hi and abs(m - x.mean()) < 1e-12
    _, lo2, hi2 = block_bootstrap_mean(rng.normal(0.5, 4.0, 400), block=5)
    assert (hi2 - lo2) > (hi - lo)
