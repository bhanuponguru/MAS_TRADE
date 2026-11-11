import numpy as np
import pandas as pd

DAYS = 252


def perf_stats(r, ppy=DAYS):
    """r: Series of per-bar simple returns; ppy = bars per year (252 daily stocks, 365*bars/day for 24/7)."""
    r = r.dropna()
    eq = (1 + r).cumprod()
    years = len(r) / ppy
    vol = r.std() * np.sqrt(ppy)
    return {
        "CAGR": eq.iloc[-1] ** (1 / years) - 1,
        "Vol": vol,
        "Sharpe": r.mean() * ppy / vol if vol > 0 else np.nan,
        "MaxDD": (eq / eq.cummax() - 1).min(),
        "HitRate": (r > 0).mean(),
    }


def metrics_table(returns, turnover=None, ppy=DAYS):
    """returns: DataFrame of per-bar returns per strategy; turnover: dict name -> annual turnover."""
    tab = pd.DataFrame({c: perf_stats(returns[c], ppy) for c in returns}).T
    if turnover is not None:
        tab["Turnover"] = pd.Series(turnover)
    return tab


def extended_stats(r, ppy=DAYS):
    """perf_stats plus Sortino (downside deviation vs 0) and Calmar (CAGR / |MaxDD|)."""
    r = r.dropna()
    out = perf_stats(r, ppy)
    dd = np.sqrt((np.minimum(r, 0.0) ** 2).mean()) * np.sqrt(ppy)
    out["Sortino"] = r.mean() * ppy / dd if dd > 0 else np.nan
    out["Calmar"] = out["CAGR"] / abs(out["MaxDD"]) if out["MaxDD"] < 0 else np.nan
    return out


def _sharpe_rows(x, ppy):
    sd = x.std(axis=-1, ddof=1)
    return np.where(sd > 0, x.mean(axis=-1) / np.where(sd > 0, sd, 1.0) * np.sqrt(ppy), np.nan)


def block_bootstrap_sharpe(r, ppy, block, ref=None, n_boot=2000, seed=0, chunk=100):
    """Moving-block bootstrap of the annualised Sharpe of r (blocks keep short-range dependence).
    With ref given, the same resampled blocks are applied to both and the Sharpe DIFFERENCE
    r - ref is returned (paired, so the common market noise cancels).
    Returns (point estimate, 5th pct, 95th pct)."""
    df = pd.concat([r, ref], axis=1).dropna() if ref is not None else r.dropna().to_frame()
    x = df.values
    n = len(x)
    block = int(min(max(block, 1), n))
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    stat = lambda a: _sharpe_rows(a[..., 0], ppy) - (_sharpe_rows(a[..., 1], ppy) if ref is not None else 0.0)
    point = float(stat(x[None])[0])
    draws = []
    for _ in range(-(-n_boot // chunk)):
        starts = rng.integers(0, n - block + 1, (chunk, nb))
        idx = (starts[:, :, None] + np.arange(block)).reshape(chunk, -1)[:, :n]
        draws.append(stat(x[idx]))
    d = np.concatenate(draws)[:n_boot]
    return point, float(np.nanpercentile(d, 5)), float(np.nanpercentile(d, 95))


def yearly_returns(df):
    """Compounded return per calendar year per column."""
    return (1 + df).groupby(df.index.year).prod() - 1


def block_bootstrap_regression(y, X, block, n_boot=2000, seed=0):
    """OLS of y (T,) on the columns of X (T, k) with an intercept, and moving-block bootstrap 5th / 95th percentiles of every
    coefficient (rows are resampled in blocks, so serial dependence is kept). Returns a DataFrame indexed by
    intercept and the columns of X; the intercept is per bar."""
    X = pd.DataFrame(X) if not isinstance(X, pd.DataFrame) else X
    df = pd.concat([pd.Series(y, name="y").reset_index(drop=True), X.reset_index(drop=True)], axis=1).dropna()
    yv, Z = df["y"].values, np.column_stack([np.ones(len(df)), df.drop(columns="y").values])
    names = ["intercept"] + [str(c) for c in X.columns]
    coef = np.linalg.lstsq(Z, yv, rcond=None)[0]
    n = len(df)
    block = int(min(max(block, 1), n))
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    draws = []
    for _ in range(n_boot):
        idx = (rng.integers(0, n - block + 1, nb)[:, None] + np.arange(block)).ravel()[:n]
        draws.append(np.linalg.lstsq(Z[idx], yv[idx], rcond=None)[0])
    d = np.array(draws)
    return pd.DataFrame({"coef": coef, "5%": np.percentile(d, 5, axis=0), "95%": np.percentile(d, 95, axis=0)}, index=names)
