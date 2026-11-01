"""Stage 1: scores -> neutral, vol-targeted books for every rebalance date (information before t only)."""
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from .agents import Ctx


def ledoit_wolf(X):
    """Ledoit-Wolf (2004) shrinkage of the sample covariance of X (T x p) toward m*I."""
    T, p = X.shape
    X = X - X.mean(0)
    S = X.T @ X / T
    m = np.trace(S) / p
    d2 = ((S - m * np.eye(p)) ** 2).sum() / p
    b2 = min(d2, ((X ** 2).sum(1) ** 2).sum() / T ** 2 / p - (S ** 2).sum() / T / p)
    k = 0.0 if d2 <= 0 else max(b2, 0.0) / d2
    return k * m * np.eye(p) + (1 - k) * S


def rank_gauss(s):
    r = np.argsort(np.argsort(s, kind="stable"), kind="stable")
    return norm.ppf((r + 0.5) / len(s))


def betas(R, rb):
    rbc = rb - rb.mean()
    return ((R - R.mean(0)) * rbc[:, None]).sum(0) / max((rbc ** 2).sum(), 1e-12)


def neutralise(w, beta):
    """Project w onto {1'w = 0, beta'w = 0}."""
    A = np.column_stack([np.ones(len(w)), beta])
    return w - A @ np.linalg.lstsq(A, w, rcond=None)[0]


def scale_book(w, Sig, target_bar, cap):
    v = np.sqrt(w @ Sig @ w)
    if v <= 1e-15:
        return np.zeros_like(w)
    w = w * target_bar / v
    g = np.abs(w).sum()
    return w * cap / g if g > cap else w


@dataclass
class BookSet:
    rebal: np.ndarray    # (K,) bar index of each rebalance
    names: list          # agent names
    tickers: list
    Z: np.ndarray        # (K, A, N) gauss scores (NaN outside the tradable set; timing: raw signal)
    Wb: np.ndarray       # (K, A, N) book weights as fractions of equity
    el: np.ndarray       # (K, N) tradable mask
    beta: np.ndarray     # (K, N) beta to BTC
    adv: np.ndarray      # (K, N) trailing daily dollar volume
    sig_d: np.ndarray    # (K, N) trailing daily vol
    idx: list            # per k: indices of the tradable assets
    Sig: list            # per k: Ledoit-Wolf per-bar covariance of the tradable assets
    pr: np.ndarray       # (n, A) per-bar return of each book held at its rebalance weights, gross of costs
    k0: int              # first rebalance every combiner trades from
    H: int
    target_bar: float    # per-bar vol target of every book


def build_books(P, cfg, agents):
    n, N = P.R.shape
    bpd = P.bpd
    Tb = int(round(cfg.hist_days * bpd))
    cov_b, beta_b, adv_b = (int(round(d * bpd)) for d in (cfg.cov_days, cfg.beta_days, cfg.adv_days))
    H = cfg.rebal_bars
    rebal = np.arange(Tb, n - 1, H)
    K, A = len(rebal), len(agents)
    target_bar = cfg.target_vol / np.sqrt(P.ppy)
    Z = np.full((K, A, N), np.nan)
    Wb, el_all = np.zeros((K, A, N)), np.zeros((K, N), bool)
    beta, adv, sig_d = np.zeros((K, N)), np.zeros((K, N)), np.zeros((K, N))
    idx, Sig = [], []
    pr = np.zeros((n, A))
    first = None
    for k, t in enumerate(rebal):
        adv_t = np.median(P.V[t - adv_b:t], axis=0) * bpd        # trailing daily dollar volume, before t
        el = P.E[t] & P.valid[t - Tb:t].all(0) & (adv_t >= cfg.min_adv)
        ii = np.flatnonzero(el)
        idx.append(ii)
        if len(ii) < cfg.min_assets:
            Sig.append(np.zeros((len(ii), len(ii))))
            continue
        first = k if first is None else first
        el_all[k] = el
        R = P.R[t - Tb:t][:, ii]
        ctx = Ctx(R, P.F[t - Tb:t][:, ii], P.V[t - Tb:t][:, ii], P.btc[t - Tb:t], [P.tickers[j] for j in ii], bpd)
        Sg = ledoit_wolf(R[-cov_b:])
        b = betas(R[-beta_b:], P.btc[t - beta_b:t])
        Sig.append(Sg)
        beta[k, ii] = b
        adv[k, ii] = adv_t[ii]
        sig_d[k, ii] = R[-cov_b:].std(0) * np.sqrt(bpd)
        for a, ag in enumerate(agents):
            s = ag.signal(ctx, cfg)
            if ag.kind == "xs":
                z = rank_gauss(s)
                Z[k, a, ii] = z
                w = scale_book(neutralise(z - z.mean(), b), Sg, target_bar, cfg.gross_cap)
            else:
                Z[k, a, ii] = s
                u = (s != 0).astype(float)
                v = np.sqrt(u @ Sg @ u)
                w = s * target_bar / v if v > 0 else np.zeros_like(s)
                g = np.abs(w).sum()
                w = w * cfg.gross_cap / g if g > cfg.gross_cap else w
            Wb[k, a, ii] = w
        e = rebal[k + 1] if k + 1 < K else n
        pr[t:e] = (P.R[t:e] - P.F[t:e]) @ Wb[k].T
    burn = int(round(cfg.burn_days * bpd))
    k0 = next((k for k in range(K) if first is not None and k >= first and rebal[k] >= rebal[first] + burn), K)
    return BookSet(rebal, [a.name for a in agents], P.tickers, Z, Wb, el_all, beta, adv, sig_d, idx, Sig, pr, k0, H, target_bar)
