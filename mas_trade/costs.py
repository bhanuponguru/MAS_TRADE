"""Liquidity-aware trading cost: fee + square-root market impact."""
import numpy as np


def trade_cost(d, adv, sig_d, fee_bps, k, aum):
    """d: trade per asset as a fraction of equity; adv: daily dollar volume; sig_d: daily vol.
    Returns the cost as a fraction of equity: sum |d| * (fee + k * sig_d * sqrt(|d| * aum / adv))."""
    a = np.abs(d)
    return float((a * (fee_bps / 1e4 + k * sig_d * np.sqrt(a * aum / np.maximum(adv, 1.0)))).sum())
