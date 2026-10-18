import numpy as np
import pandas as pd

DAYS = 252


def perf_stats(r):
    """r: Series of daily simple returns."""
    r = r.dropna()
    eq = (1 + r).cumprod()
    years = len(r) / DAYS
    vol = r.std() * np.sqrt(DAYS)
    return {
        "CAGR": eq.iloc[-1] ** (1 / years) - 1,
        "Vol": vol,
        "Sharpe": r.mean() * DAYS / vol if vol > 0 else np.nan,
        "MaxDD": (eq / eq.cummax() - 1).min(),
        "HitRate": (r > 0).mean(),
    }


def metrics_table(returns, turnover=None):
    """returns: DataFrame of daily returns per strategy; turnover: dict name -> annual turnover."""
    tab = pd.DataFrame({c: perf_stats(returns[c]) for c in returns}).T
    if turnover is not None:
        tab["Turnover"] = pd.Series(turnover)
    return tab
