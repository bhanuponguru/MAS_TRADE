"""Signal quality, regimes and multiple-testing control."""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr
from scipy.stats import norm

EULER = 0.5772156649015329


def _rank(x):
    return np.argsort(np.argsort(x, kind="stable"), kind="stable").astype(float)


def rank_ic(score, fwd):
    """Cross-sectional rank correlation between a score vector and the realised forward returns (NaN-safe).
    Uses FUTURE returns: for diagnostics only, never for decisions."""
    ok = np.isfinite(score) & np.isfinite(fwd)
    if ok.sum() < 8 or np.std(score[ok]) == 0:
        return np.nan
    return float(np.corrcoef(_rank(score[ok]), _rank(fwd[ok]))[0, 1])


def ic_summary(ics):
    """Mean rank-IC, its t-stat, hit rate and count over a series of per-date ICs."""
    x = np.asarray(ics, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return {"IC": np.nan, "t": np.nan, "IC>0": np.nan, "n": len(x)}
    return {"IC": x.mean(), "t": x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), "IC>0": (x > 0).mean(), "n": len(x)}


def regime_labels(btc, bpd, index, trend_days=90, vol_days=30):
    """bull/bear (sign of the trailing BTC return) x hi/lo vol (trailing vol vs its expanding median), all known before the bar."""
    b = pd.Series(btc, index=index)
    trend = b.rolling(int(trend_days * bpd)).sum().shift(1)
    vol = b.rolling(int(vol_days * bpd)).std().shift(1)
    hi = vol > vol.expanding(min_periods=int(vol_days * bpd)).median()
    lab = np.where(trend > 0, "bull", "bear").astype(object) + np.where(hi, "/hiVol", "/loVol").astype(object)
    return pd.Series(lab, index=index).where(trend.notna() & vol.notna())


def regime_table(df, labels, ppy):
    out = {}
    for lab, g in df.groupby(labels.reindex(df.index)):
        sd = g.std()
        out[lab] = (g.mean() * ppy / sd.replace(0, np.nan) / np.sqrt(ppy)).to_dict() | {"bars": len(g)}
    return pd.DataFrame(out).T


def deflated_sharpe(sr, n_trials, sr_var, skew, kurt, T):
    """Bailey & Lopez de Prado (2014). sr and sr_var per period; kurt is raw (3 = normal); T = number of periods."""
    n = max(int(n_trials), 2)
    best_null = np.sqrt(max(sr_var, 0.0)) * ((1 - EULER) * norm.ppf(1 - 1 / n) + EULER * norm.ppf(1 - 1 / (n * np.e)))
    return float(ndtr((sr - best_null) * np.sqrt(T - 1) / np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2)))


def log_trial(path, **row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), **row}) + "\n")


def read_trials(path):
    p = Path(path)
    return pd.DataFrame([json.loads(l) for l in p.read_text().splitlines()]) if p.exists() else pd.DataFrame()


def block_bootstrap_mean(x, block=5, n_boot=2000, seed=0):
    """Moving-block bootstrap of the mean of x. Returns (mean, 5th pct, 95th pct)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    block = int(min(max(block, 1), n))
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    starts = rng.integers(0, n - block + 1, (n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :n]
    d = x[idx].mean(1)
    return float(x.mean()), float(np.percentile(d, 5)), float(np.percentile(d, 95))
