"""Market panel for the v2 engine: returns, eligibility, funding, dollar volume, BTC on one bar grid."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import crypto_data as cd


@dataclass
class Panel:
    R: np.ndarray        # (n, N) per-bar price returns, NaN -> 0
    valid: np.ndarray    # (n, N) bool, the asset traded on that bar
    E: np.ndarray        # (n, N) bool, point-in-time universe membership
    F: np.ndarray        # (n, N) funding per bar paid by longs
    V: np.ndarray        # (n, N) dollar volume per bar
    btc: np.ndarray      # (n,) BTC return (0 where missing)
    dates: pd.DatetimeIndex
    tickers: list
    bpd: int

    @property
    def ppy(self):
        return 365.0 * self.bpd


def make_panel(rets, elig, fund, vol, btc, bpd):
    raw = rets.values
    valid = ~np.isnan(raw)
    N = lambda df: np.nan_to_num(df.reindex_like(rets).values)
    b = np.zeros(len(rets)) if btc is None else np.nan_to_num(btc.reindex(rets.index).values)
    return Panel(np.where(valid, raw, 0.0), valid, elig.reindex_like(rets).fillna(False).values.astype(bool),
                 N(fund), N(vol), b, rets.index, list(rets.columns), bpd)


def load_crypto_panel(bar, universe="broad"):
    uni = cd.load_universe(universe)
    rets, elig, fund, btc = cd.load_panel(bar, universe=uni)
    vol = cd._read(cd.crypto_dir(), bar, list(rets.columns), "quote_volume")
    return make_panel(rets, elig, fund, vol, btc, {"1d": 1, "4h": 6, "1h": 24, "15m": 96, "5m": 288}[bar])
