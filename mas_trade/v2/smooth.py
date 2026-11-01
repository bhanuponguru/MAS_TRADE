"""Cost-aware partial adjustment (Garleanu-Pedersen style). Trading from the previous weights p toward the
target tau minimises  gamma*var*H/2 (w - tau)^2 + lam/2 (w - p)^2  per asset, so  w = p + eta (tau - p)  with
eta = a / (a + lam),  a = gamma*var*H.  lam is set so the quadratic cost equals the linear cost rate c at the
typical position size d_ref:  lam = 2c / d_ref,  c = fee + k*sigma_d*sqrt(d_ref*aum/ADV)."""
from dataclasses import replace

import numpy as np


def cost_aware_eta(sig_d, adv, d_ref, cfg):
    sig_bar = sig_d / np.sqrt(cfg.bpd)
    a = cfg.risk_aversion * sig_bar ** 2 * cfg.rebal_bars
    c = cfg.fee_bps / 1e4 + cfg.impact_k * sig_d * np.sqrt(d_ref * cfg.aum / np.maximum(adv, 1.0))
    den = a + 2 * c / d_ref
    return np.where(den > 0, a / np.where(den > 0, den, 1.0), 1.0)


def cost_aware_smooth(bs, cfg, W, project=True):
    """Rows before bs.k0 untouched; assets that leave the tradable set are closed (eta = 1 there). The smoothed
    weights keep the target's net dollar and beta exposure (zero for the neutral books, the timing view for Timing)."""
    out, prev = W.copy(), np.zeros(W.shape[1])
    for k in range(bs.k0, len(bs.rebal)):
        ii, tgt = bs.idx[k], W[k]
        eta = np.ones(W.shape[1])
        if len(ii) and np.abs(tgt[ii]).sum() > 0:
            eta[ii] = cost_aware_eta(bs.sig_d[k, ii], bs.adv[k, ii], np.abs(tgt[ii]).sum() / len(ii), cfg)
        new = prev + eta * (tgt - prev)
        if len(ii) and project:          # per-asset speeds break neutrality: restore the target's dollar and beta exposure
            A = np.column_stack([np.ones(len(ii)), bs.beta[k, ii]])
            new[ii] += A @ np.linalg.lstsq(A.T @ A, A.T @ (tgt[ii] - new[ii]), rcond=None)[0]
        prev = new
        out[k] = prev
    return out


def smooth_books(bs, P, cfg):
    """Cost-aware execution of every agent's book on its own (the timing book is not projected: it owns
    net exposure). Returns a BookSet whose books and paper returns are the smoothed ones, so combiners
    mix what the agents would really hold."""
    Wb = bs.Wb.copy()
    for a, name in enumerate(bs.names):
        Wb[:, a] = cost_aware_smooth(bs, cfg, bs.Wb[:, a], project=name != "Timing")
    pr = np.zeros_like(bs.pr)
    for k, t in enumerate(bs.rebal):
        e = bs.rebal[k + 1] if k + 1 < len(bs.rebal) else len(P.R)
        pr[t:e] = (P.R[t:e] - P.F[t:e]) @ Wb[k].T
    return replace(bs, Wb=Wb, pr=pr)
