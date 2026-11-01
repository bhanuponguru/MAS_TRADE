"""Stage 2: combiners. Each maps the books (information before the rebalance only) to system weights W (K, N)."""
import numpy as np

from .books import ledoit_wolf, scale_book
from .diagnostics import realised_ic
from .smooth import cost_aware_smooth


def _rescale(bs, cfg, ppy, k, w):
    ii = bs.idx[k]
    out = np.zeros_like(w)
    out[ii] = scale_book(w[ii], bs.Sig[k], cfg.target_vol / np.sqrt(ppy), cfg.gross_cap)
    return out


def _past_vol(bs, cfg, k):
    t = bs.rebal[k]
    win = bs.pr[max(0, t - int(round(cfg.cov_days * cfg.bpd))):t]
    return np.maximum(win.std(0), 1e-12)


def single_book(bs, cfg, a):
    W = np.zeros((len(bs.rebal), bs.Wb.shape[2]))
    W[bs.k0:] = bs.Wb[bs.k0:, a]
    return W


def equal_weight(bs, cfg):
    W = np.zeros((len(bs.rebal), bs.Wb.shape[2]))
    for k in range(bs.k0, len(bs.rebal)):
        W[k] = _rescale(bs, cfg, cfg.ppy, k, bs.Wb[k].mean(0))
    return W


def inverse_vol(bs, cfg):
    W = np.zeros((len(bs.rebal), bs.Wb.shape[2]))
    for k in range(bs.k0, len(bs.rebal)):
        b = 1.0 / _past_vol(bs, cfg, k)
        W[k] = _rescale(bs, cfg, cfg.ppy, k, (b / b.sum()) @ bs.Wb[k])
    return W


# ---------------------------------------------------------------- C2: reward (Fixed-Share Hedge)
def fixed_share_budgets(gains, alpha, lr):
    """gains: (K, A) period gain of each book, row k known only after period k. Returns (K, A): row k is the
    budget used in period k, built from gains[:k]. Hedge update with a fixed-share mix:
    logw += lr * gain;  w = softmax(logw);  w <- (1 - alpha) w + alpha / A  (alpha = 0 is plain Hedge)."""
    K, A = gains.shape
    pi = np.full((K, A), 1.0 / A)
    logw = np.zeros(A)
    w = np.full(A, 1.0 / A)
    for k in range(1, K):
        logw = np.log(w) + lr * gains[k - 1]
        w = np.exp(logw - logw.max())
        w /= w.sum()
        w = (1 - alpha) * w + alpha / A
        pi[k] = w
    return pi


def book_gains(bs, clip=3.0):
    """Period return of each book over its ex-ante period vol (books are vol-targeted), clipped."""
    K, A = len(bs.rebal), bs.Wb.shape[1]
    g = np.zeros((K, A))
    for k, t in enumerate(bs.rebal):
        e = bs.rebal[k + 1] if k + 1 < K else len(bs.pr)
        g[k] = bs.pr[t:e].sum(0)
    unit = np.array([bs.target_bar * np.sqrt(bs.H)] * A)
    return np.clip(g / unit, -clip, clip)


def hedge_params(cfg, A, clip=3.0):
    """alpha = H / expected regime length; lr = sqrt(8 ln A / T_eff) / gain range with T_eff = 1/alpha."""
    alpha = min(1.0, cfg.rebal_bars / (cfg.regime_days * cfg.bpd))
    return alpha, np.sqrt(8 * np.log(A) * alpha) / (2 * clip)


# ---------------------------------------------------------------- C1: risk (risk budgeting)
def risk_budget_weights(Sig, pi, iters=500):
    """b >= 0, sum b = 1 with risk contributions b_i (Sig b)_i proportional to pi_i (equal risk contribution
    when pi is uniform). Fixed-point iteration b <- b sqrt(pi / rc)."""
    pi = np.asarray(pi, float) / np.sum(pi)
    b = 1.0 / np.sqrt(np.maximum(np.diag(Sig), 1e-18))
    b /= b.sum()
    for _ in range(iters):
        rc = b * (Sig @ b)
        rc = rc / rc.sum()
        b = b * np.sqrt(pi / np.maximum(rc, 1e-12))
        b /= b.sum()
    return b


def _book_cov(bs, cfg, k):
    t = bs.rebal[k]
    win = bs.pr[max(0, t - int(round(cfg.cov_days * cfg.bpd))):t]
    return ledoit_wolf(win) if len(win) > 5 else np.eye(win.shape[1])


def _mix(bs, cfg, weights_fn):
    W = np.zeros((len(bs.rebal), bs.Wb.shape[2]))
    for k in range(bs.k0, len(bs.rebal)):
        W[k] = _rescale(bs, cfg, cfg.ppy, k, weights_fn(k) @ bs.Wb[k])
    return W


def hedge_only(bs, cfg):
    """C2 alone: budgets from Fixed-Share Hedge, applied per unit of past book vol, no correlation term."""
    A = bs.Wb.shape[1]
    pi = fixed_share_budgets(book_gains(bs), *hedge_params(cfg, A))
    def f(k):
        b = pi[k] / _past_vol(bs, cfg, k)
        return b / b.sum()
    return _mix(bs, cfg, f)


def risk_budget_only(bs, cfg):
    """C1 alone: equal risk contributions over the shrunk book covariance."""
    A = bs.Wb.shape[1]
    return _mix(bs, cfg, lambda k: risk_budget_weights(_book_cov(bs, cfg, k), np.ones(A)))


def hedge_risk_budget(bs, cfg):
    """C1 + C2: Fixed-Share Hedge sets each book's risk budget, risk budgeting turns budgets into weights."""
    A = bs.Wb.shape[1]
    pi = fixed_share_budgets(book_gains(bs), *hedge_params(cfg, A))
    return _mix(bs, cfg, lambda k: risk_budget_weights(_book_cov(bs, cfg, k), pi[k]))


# ---------------------------------------------------------------- C3: view fusion
def causal_ic(bs, P, cfg, xs):
    """(K, M) EWMA of each cross-sectional agent's realised rank-IC from periods that ended before rebalance k,
    shrunk toward 0 with cfg.ic_prior pseudo-observations."""
    ic = realised_ic(bs, P, 1)[:, xs]
    K, M = ic.shape
    lam = 0.5 ** (1.0 / cfg.ic_halflife)
    out = np.zeros((K, M))
    for k in range(1, K):
        past = ic[:k]
        w = lam ** np.arange(k - 1, -1, -1)[:, None] * np.isfinite(past)
        out[k] = (np.nan_to_num(past) * w).sum(0) / (w.sum(0) + cfg.ic_prior)
    return out


def fusion_coefficients(Rz, ic):
    """Regression of the return on correlated unit-variance scores: beta = R_z^-1 IC. Independent scores give
    beta = IC (sum of calibrated views); duplicated scores share their IC between them."""
    return np.linalg.solve(Rz, ic)


def fused_views(bs, cfg, ic_hat, xs):
    """(K, N) expected return over one holding period: mu_i = sigma_H,i * beta . z_i."""
    K, N = len(bs.rebal), bs.Wb.shape[2]
    mu = np.zeros((K, N))
    M = len(xs)
    for k in range(bs.k0, K):
        G, n = np.zeros((M, M)), 0
        for j in range(max(0, k - cfg.z_window + 1), k + 1):
            ii = bs.idx[j]
            if len(ii) >= cfg.min_assets:
                Zj = bs.Z[j][np.ix_(xs, ii)]
                G, n = G + Zj @ Zj.T / len(ii), n + 1
        Rz = (1 - cfg.z_shrink) * G / max(n, 1) + cfg.z_shrink * np.eye(M)
        beta = fusion_coefficients(Rz, ic_hat[k])
        ii = bs.idx[k]
        sig_h = bs.sig_d[k, ii] / np.sqrt(cfg.bpd) * np.sqrt(bs.H)
        mu[k, ii] = sig_h * (beta @ bs.Z[k][np.ix_(xs, ii)])
    return mu


def mean_variance_book(bs, cfg, k, mu_k, cov=None):
    """w = Sigma_H^-1 (mu - A nu) / gamma with A = [1, beta]: dollar- and beta-neutral, sized by conviction
    (scaled down, never up, to the vol target and the gross cap)."""
    ii = bs.idx[k]
    w = np.zeros(bs.Wb.shape[2])
    if len(ii) < cfg.min_assets or not np.any(mu_k[ii]):
        return w
    S = bs.Sig[k] * bs.H
    if (cov or cfg.fusion_cov) == "diag":     # inverting a noisy full covariance loads on noise: use per-asset variances
        S = np.diag(np.diag(S))
    A = np.column_stack([np.ones(len(ii)), bs.beta[k, ii]])
    x, Y = np.linalg.solve(S, mu_k[ii]), np.linalg.solve(S, A)
    v = (x - Y @ np.linalg.solve(A.T @ Y, A.T @ x)) / cfg.risk_aversion
    vol = np.sqrt(v @ bs.Sig[k] @ v)
    target = cfg.target_vol / np.sqrt(cfg.ppy)
    if vol > target:
        v = v * target / vol
    g = np.abs(v).sum()
    w[ii] = v * cfg.gross_cap / g if g > cfg.gross_cap else v
    return w


def view_fusion(bs, P, cfg, timing_weight=0.0, cov=None):
    """C3: IC-calibrated views of the cross-sectional agents are fused with the correlation-aware regression
    coefficients, turned into one mean-variance book, executed cost-aware; optionally plus a share of the timing book."""
    xs = [i for i, n in enumerate(bs.names) if n != "Timing"]
    mu = fused_views(bs, cfg, causal_ic(bs, P, cfg, xs), xs)
    W = np.zeros_like(mu)
    for k in range(bs.k0, len(bs.rebal)):
        W[k] = mean_variance_book(bs, cfg, k, mu[k], cov)
    W = cost_aware_smooth(bs, cfg, W, project=True)
    if timing_weight:
        W = W + timing_weight * single_book(bs, cfg, bs.names.index("Timing"))
    return W
