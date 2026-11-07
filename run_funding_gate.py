"""Mechanical gate for carry rung R1 (experiment 014), no P&L: is the funding forecast from the premium better than the
trailing mean funding that rung 0 implicitly uses?

python run_funding_gate.py

At every dev-period rebalance date and for every tradable coin: forecast of the funding sum over the next holding period
against the realised sum, compared by the cross-sectionally demeaned squared error (the agents trade differences between
coins). The 90% bootstrap interval resamples rebalance dates in blocks of 5.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from mas_trade.config import EngineConfig
from mas_trade.diagnostics import block_bootstrap_mean
from mas_trade.engine import tradable
from mas_trade.funding import forecast_funding_sum
from mas_trade.panel import load_crypto_panel

CARRY_DAYS = 14.0                       # rung 0's trailing window
rows = {}
for bar in ("1d", "4h", "1h"):
    cfg = EngineConfig.for_tier(bar)
    P = load_crypto_panel(bar, "broad", with_premium=True)
    cut = P.dates[-1] - pd.DateOffset(months=cfg.holdout_months)
    end = int((P.dates < cut).sum())
    H, Tb, hpb = cfg.rebal_bars, int(round(cfg.hist_days * P.bpd)), P.hpb
    cb = int(round(CARRY_DAYS * P.bpd))
    e0, e1, z, n_coins = [], [], [], []
    for t in range(Tb, end - H, H):
        ii, _ = tradable(P, cfg, t)
        if len(ii) < cfg.min_assets:
            continue
        f1 = forecast_funding_sum(P.prem[(t - Tb) * hpb:t * hpb][:, ii].astype(float), H * hpb)
        f0 = P.F[t - cb:t][:, ii].mean(0) * H
        y = P.F[t:t + H][:, ii].sum(0)
        ok = np.isfinite(f1)
        if ok.sum() < cfg.min_assets:
            continue
        dm = lambda v: v[ok] - v[ok].mean()
        y, f0, f1 = dm(y), dm(f0), dm(f1)
        e0.append(np.mean((y - f0) ** 2))
        e1.append(np.mean((y - f1) ** 2))
        z.append(np.mean(y ** 2))
        n_coins.append(ok.sum())
    e0, e1, z = map(np.array, (e0, e1, z))
    d, lo, hi = block_bootstrap_mean(e0 - e1, block=5)
    rows[bar] = {"dates": len(e0), "coins": float(np.mean(n_coins)), "R2 rung0 (trailing mean)": 1 - e0.sum() / z.sum(),
                 "R2 R1 (premium forecast)": 1 - e1.sum() / z.sum(), "MSE0-MSE1": d, "5%": lo, "95%": hi, "pass": lo > 0}
res = pd.DataFrame(rows).T
pd.options.display.float_format = "{:.4g}".format
print(res.to_string())
print("gate:", "PASS" if res["pass"].astype(bool).sum() >= 2 else "FAIL", "(needs the lower bound above 0 on at least two of three bar sizes)")
out = Path("docs/experiments/data/014")
out.mkdir(parents=True, exist_ok=True)
res.to_csv(out / "gate.csv")
