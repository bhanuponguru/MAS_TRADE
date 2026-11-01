"""Signal quality, P&L decomposition, regimes and multiple-testing control."""
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


def realised_ic(bs, P, mult=1, end=None):
    """(K, A) rank-IC between each agent's score at rebalance k and the realised return over the next
    mult*H bars (NaN for timing, outside the data, or beyond `end`). Uses FUTURE returns: for
    diagnostics only, never for decisions."""
    K, A, _ = bs.Z.shape
    out = np.full((K, A), np.nan)
    n = len(P.R)
    for k in range(K):
        t, e = bs.rebal[k], bs.rebal[k] + mult * bs.H
        if e > (end or n) or len(bs.idx[k]) < 8 or not bs.el[k].any():
            continue
        ii = bs.idx[k]
        ok = P.valid[t:e][:, ii].all(0)
        if ok.sum() < 8:
            continue
        fwd = (1.0 + P.R[t:e][:, ii]).prod(0) - 1.0
        for a in range(A):
            if np.nanstd(bs.Z[k, a, ii]) == 0 or bs.names[a] == "Timing":
                continue
            out[k, a] = np.corrcoef(_rank(bs.Z[k, a, ii][ok]), _rank(fwd[ok]))[0, 1]
    return out


def ic_table(bs, P, end=None, mults=(1, 2, 4)):
    ics = {m: realised_ic(bs, P, m, end) for m in mults}
    rows = {}
    for a, name in enumerate(bs.names):
        x = ics[mults[0]][bs.k0:, a]
        x = x[np.isfinite(x)]
        if len(x) < 3:
            continue
        rows[name] = {"IC": x.mean(), "t": x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), "IC>0": (x > 0).mean(), "n": len(x),
                      **{f"IC@{m}H": np.nanmean(ics[m][bs.k0:, a]) for m in mults[1:]}}
    return pd.DataFrame(rows).T


def decompose(ex, ppy, sl=slice(None)):
    """Annualised arithmetic contribution of each component. total = market + selection + funding - cost."""
    m = lambda s: s.iloc[sl].mean() * ppy
    d = {"market": m(ex.market), "selection": m(ex.selection), "funding": m(ex.funding), "cost": -m(ex.cost)}
    d["total"] = sum(d.values())
    d["check"] = m(ex.net)    # equals total
    return d


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
