"""Download daily adjusted closes once with yfinance, cache them as CSV."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def download_prices(symbols, start, end, path):
    import yfinance as yf

    raw = yf.download(list(symbols), start=start, end=end, auto_adjust=True, progress=False)
    prices = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    prices = prices.dropna(how="all")
    if prices.empty:
        raise RuntimeError("yfinance returned no data (network / rate limit?)")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(path)
    return prices


def load_prices(cfg, refresh=False):
    path = ROOT / "data" / "prices.csv"
    if refresh or not path.exists():
        download_prices(cfg.tickers + [cfg.benchmark], cfg.start, cfg.end, path)
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    need = cfg.tickers + [cfg.benchmark]
    missing = [t for t in need if t not in prices.columns]
    if missing:
        raise RuntimeError(f"cached prices lack {missing}; rerun with refresh=True")
    return prices[need].dropna()


def load_returns(cfg, refresh=False):
    """Simple daily returns. Returns (stock_returns DataFrame, benchmark_returns Series)."""
    rets = load_prices(cfg, refresh).pct_change().dropna()
    return rets[cfg.tickers], rets[cfg.benchmark]
