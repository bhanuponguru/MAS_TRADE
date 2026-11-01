"""v2 strategy agents. Each maps the PAST window of the tradable assets to a raw signal (higher = expected
to do better). Cross-sectional agents ("xs") are turned into dollar- and beta-neutral books by books.py;
the timing agent ("ts") owns the net exposure and trades BTC only. Windows are in days (Ctx.bars)."""
from dataclasses import dataclass

import numpy as np


@dataclass
class Ctx:
    R: np.ndarray       # (T, n) past per-bar returns of the tradable assets (no NaN)
    F: np.ndarray       # (T, n) past funding per bar
    V: np.ndarray       # (T, n) past dollar volume per bar
    btc: np.ndarray     # (T,) past BTC returns
    names: list         # tickers of the n assets
    bpd: int

    def bars(self, days):
        return max(1, int(round(days * self.bpd)))


def _vol(x):
    return np.maximum(x.std(0), 1e-12)


class XSMomentum:
    name, kind = "XSMomentum", "xs"

    def signal(self, c, cfg):
        L, S = c.bars(cfg.mom_days), c.bars(cfg.skip_days)
        r = c.R[-(L + S):-S]
        return r.sum(0) / (_vol(r) * np.sqrt(len(r)))


class ResidualReversal:
    name, kind = "ResidualReversal", "xs"

    def signal(self, c, cfg):
        B = c.bars(cfg.beta_days)
        rb, R = c.btc[-B:], c.R[-B:]
        beta = ((R - R.mean(0)) * (rb - rb.mean())[:, None]).sum(0) / max(((rb - rb.mean()) ** 2).sum(), 1e-12)
        resid = R - rb[:, None] * beta
        n = c.bars(cfg.rev_days)
        return -resid[-n:].sum(0) / (_vol(resid) * np.sqrt(n))


class FundingCarry:
    name, kind = "FundingCarry", "xs"

    def signal(self, c, cfg):    # longs pay funding when it is positive: long low funding, short high
        return -c.F[-c.bars(cfg.carry_days):].mean(0)


class SizeLiquidity:
    name, kind = "SizeLiquidity", "xs"

    def signal(self, c, cfg):    # small (low dollar volume) minus large
        return -np.log1p(np.median(c.V[-c.bars(cfg.size_days):], axis=0))


class Timing:
    name, kind = "Timing", "ts"

    def signal(self, c, cfg):    # tanh of BTC's trailing t-stat, on the BTC column only
        r = c.btc[-c.bars(cfg.timing_days):]
        s = np.zeros(len(c.names))
        if "BTCUSDT" in c.names:
            s[c.names.index("BTCUSDT")] = np.tanh(r.sum() / (max(r.std(), 1e-12) * np.sqrt(len(r))))
        return s


def default_v2_agents():
    return [XSMomentum(), ResidualReversal(), FundingCarry(), SizeLiquidity(), Timing()]
