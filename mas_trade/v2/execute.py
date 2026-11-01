"""Stage 3: turn target weights (fractions of equity) into net P&L with drift, funding and costs."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .costs import trade_cost


@dataclass
class ExecResult:
    net: pd.Series        # per-bar net return
    price: pd.Series      # price P&L / equity at the start of the bar
    funding: pd.Series    # funding P&L (negative when longs pay)
    cost: pd.Series       # trading cost (positive number)
    market: pd.Series     # beta-weighted net exposure * BTC return
    exposure: pd.Series   # net beta exposure at the start of the bar
    gross: pd.Series      # gross exposure at the start of the bar
    turnover: float       # annual sum |dw|

    @property
    def selection(self):
        return self.price - self.market


def execute(P, bs, W, cfg):
    """W: (K, N) target weights per rebalance (rows before bs.k0 are ignored). Equity starts at 1."""
    n, N = P.R.shape
    K = len(bs.rebal)
    t_start = bs.rebal[bs.k0] if bs.k0 < K else n
    out = {k: np.zeros(n) for k in ("net", "price", "funding", "cost", "market", "exposure", "gross")}
    eq, h, turn = 1.0, np.zeros(N), 0.0
    for k in range(bs.k0, K):
        t = bs.rebal[k]
        e = bs.rebal[k + 1] if k + 1 < K else n
        tgt = W[k] * eq
        d = tgt - h
        c = trade_cost(d, bs.adv[k], bs.sig_d[k], cfg.fee_bps, cfg.impact_k, cfg.aum)
        turn += np.abs(d).sum() / eq
        h = tgt
        for b in range(t, e):
            ex = bs.beta[k] @ h
            pnl_p, pnl_f = h @ P.R[b], -h @ P.F[b]
            eq1 = eq + pnl_p + pnl_f - (c if b == t else 0.0)
            out["price"][b], out["funding"][b] = pnl_p / eq, pnl_f / eq
            out["cost"][b] = (c / eq) if b == t else 0.0
            out["exposure"][b], out["market"][b] = ex / eq, ex / eq * P.btc[b]
            out["gross"][b] = np.abs(h).sum() / eq
            out["net"][b] = eq1 / eq - 1.0
            h = h * (1.0 + P.R[b])
            eq = eq1
    idx = P.dates[t_start:]
    s = {k: pd.Series(v[t_start:], index=idx) for k, v in out.items()}
    years = max(len(idx) / P.ppy, 1e-9)
    return ExecResult(turnover=turn / years, **s)
