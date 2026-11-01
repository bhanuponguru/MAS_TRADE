import numpy as np
import pandas as pd

from mas_trade.config import V2Config
from mas_trade.v2 import combiners as cb
from mas_trade.v2.agents import default_v2_agents
from mas_trade.v2.books import build_books, ledoit_wolf, neutralise, rank_gauss, scale_book
from mas_trade.v2.costs import trade_cost
from mas_trade.v2.diagnostics import deflated_sharpe, ic_table
from mas_trade.v2.execute import execute
from mas_trade.v2.panel import make_panel

CFG = V2Config(bpd=1, rebal_bars=5, hist_days=60, mom_days=30, skip_days=3, rev_days=3, carry_days=10, size_days=10,
               timing_days=20, beta_days=30, cov_days=30, adv_days=10, burn_days=20, min_adv=1.0)


def make_panel_synth(n=400, N=14, seed=0, funding=0.0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-01", periods=n, freq="D", tz="UTC")
    cols = ["BTCUSDT"] + [f"S{i}" for i in range(N - 1)]
    btc = rng.normal(0.0005, 0.03, n)
    r = 0.8 * btc[:, None] + rng.normal(0, 0.03, (n, N))
    r[:, 0] = btc
    rets = pd.DataFrame(r, index=idx, columns=cols)
    ones = pd.DataFrame(1.0, index=idx, columns=cols)
    fund = pd.DataFrame(funding, index=idx, columns=cols)
    vol = ones * (1e7 * rng.uniform(0.5, 2, N))
    return make_panel(rets, ones.astype(bool), fund, vol, pd.Series(btc, index=idx), 1)


def test_books_neutral_and_vol_targeted():
    P = make_panel_synth()
    bs = build_books(P, CFG, default_v2_agents())
    target = CFG.target_vol / np.sqrt(P.ppy)
    for k in range(bs.k0, len(bs.rebal)):
        ii = bs.idx[k]
        for a, n in enumerate(bs.names):
            w = bs.Wb[k, a, ii]
            if n == "Timing":
                continue
            assert abs(w.sum()) < 1e-9 and abs(bs.beta[k, ii] @ w) < 1e-9
            assert abs(np.sqrt(w @ bs.Sig[k] @ w) - target) < 1e-9 or np.abs(w).sum() >= CFG.gross_cap - 1e-9
            assert np.abs(w).sum() <= CFG.gross_cap + 1e-9


def test_ledoit_wolf_is_psd_and_shrinks():
    X = np.random.default_rng(0).normal(size=(30, 20))
    S = ledoit_wolf(X)
    assert np.linalg.eigvalsh(S).min() > 0
    assert np.linalg.cond(S) < np.linalg.cond(np.cov(X.T, bias=True))


def test_neutralise_and_rank_gauss():
    rng = np.random.default_rng(1)
    w, b = rng.normal(size=10), rng.uniform(0.5, 1.5, 10)
    v = neutralise(w, b)
    assert abs(v.sum()) < 1e-12 and abs(b @ v) < 1e-12
    z = rank_gauss(rng.normal(size=1000))
    assert abs(z.mean()) < 0.01 and abs(z.std() - 1) < 0.05


def test_trade_cost_monotone_in_size_and_inverse_in_adv():
    c = lambda d, adv: trade_cost(np.array([d]), np.array([adv]), np.array([0.05]), 5.0, 1.0, 1e6)
    assert c(0.02, 1e7) > c(0.01, 1e7) > 0
    assert c(0.01, 1e6) > c(0.01, 1e7)
    assert np.isclose(c(0.01, 1e7), 0.01 * (5e-4 + 0.05 * np.sqrt(0.01 * 1e6 / 1e7)))


def test_execute_zero_cost_matches_hand_computation():
    P = make_panel_synth(n=200, N=10)
    cfg = V2Config(**{**CFG.__dict__, "fee_bps": 0.0, "impact_k": 0.0})
    bs = build_books(P, cfg, default_v2_agents())
    W = cb.single_book(bs, cfg, 0)
    ex = execute(P, bs, W, cfg)
    eq, h = 1.0, np.zeros(P.R.shape[1])
    K = len(bs.rebal)
    ref = []
    for k in range(bs.k0, K):
        t, e = bs.rebal[k], bs.rebal[k + 1] if k + 1 < K else len(P.R)
        h = W[k] * eq
        for b in range(t, e):
            new = eq + h @ P.R[b] - h @ P.F[b]
            ref.append(new / eq - 1)
            h, eq = h * (1 + P.R[b]), new
    assert np.allclose(ex.net.values, ref)


def test_decomposition_sums_to_net():
    P = make_panel_synth(n=200, N=10, funding=0.001)
    bs = build_books(P, CFG, default_v2_agents())
    ex = execute(P, bs, cb.equal_weight(bs, CFG), CFG)
    total = ex.market + ex.selection + ex.funding - ex.cost
    assert np.allclose(total.values, ex.net.values)


def test_funding_flips_pnl_sign_for_a_long():
    P = make_panel_synth(n=120, N=10, funding=0.001)
    bs = build_books(P, CFG, default_v2_agents())
    W = np.zeros((len(bs.rebal), len(P.tickers)))
    W[bs.k0:, 1] = 1.0                                   # always long one asset
    ex = execute(P, bs, W, CFG)
    assert (ex.funding.iloc[1:] < 0).all()


def test_no_lookahead_in_books():
    P = make_panel_synth(n=300)
    cut = 200
    bs1 = build_books(P, CFG, default_v2_agents())
    P2 = make_panel_synth(n=300)
    rng = np.random.default_rng(9)
    P2.R[cut:] = rng.normal(0, 0.1, P2.R[cut:].shape)
    P2.F[cut:] = 0.01
    P2.V[cut:] *= 5
    P2.btc[cut:] = rng.normal(0, 0.1, len(P2.btc[cut:]))
    bs2 = build_books(P2, CFG, default_v2_agents())
    ks = [k for k, t in enumerate(bs1.rebal) if t <= cut]
    assert len(ks) > 10
    for k in ks:
        assert np.array_equal(bs1.Wb[k], bs2.Wb[k])
        assert np.array_equal(bs1.Z[k], bs2.Z[k], equal_nan=True)
    assert np.array_equal(bs1.pr[:cut], bs2.pr[:cut])
    w1, w2 = cb.inverse_vol(bs1, CFG), cb.inverse_vol(bs2, CFG)
    assert all(np.array_equal(w1[k], w2[k]) for k in ks)


def test_invvol_and_ew_hit_vol_target_or_cap():
    P = make_panel_synth()
    bs = build_books(P, CFG, default_v2_agents())
    for W in (cb.equal_weight(bs, CFG), cb.inverse_vol(bs, CFG)):
        for k in range(bs.k0, len(bs.rebal)):
            ii = bs.idx[k]
            v = np.sqrt(W[k, ii] @ bs.Sig[k] @ W[k, ii])
            assert abs(v - CFG.target_vol / np.sqrt(P.ppy)) < 1e-9 or np.abs(W[k]).sum() >= CFG.gross_cap - 1e-9


def test_scale_book_cap():
    Sig = np.eye(3) * 1e-6
    w = scale_book(np.array([1.0, -1.0, 0.5]), Sig, 0.1, 3.0)
    assert np.isclose(np.abs(w).sum(), 3.0)


def test_signals_have_ic_on_planted_effect():
    """Plant a cross-sectional predictability in the carry signal: IC must come out clearly positive."""
    P = make_panel_synth(n=500, N=20, seed=3)
    rng = np.random.default_rng(3)
    drift = rng.normal(0, 1, 20)
    P.F[:] = (-drift * 1e-4)[None, :] + rng.normal(0, 1e-5, P.F.shape)  # funding is low where the future drift is high
    P.R += (drift * 0.002)[None, :]
    bs = build_books(P, CFG, default_v2_agents())
    t = ic_table(bs, P)
    assert t.loc["FundingCarry", "IC"] > 0.1 and t.loc["FundingCarry", "t"] > 3 and abs(t.loc["SizeLiquidity", "IC"]) < 0.1


def test_deflated_sharpe_reference_and_monotonicity():
    # more trials -> higher bar -> lower DSR; zero-variance trials -> DSR is just a Sharpe t-test
    kw = dict(sr_var=0.01 ** 2, skew=0.0, kurt=3.0, T=1000)
    lo, hi = deflated_sharpe(0.05, 100, **kw), deflated_sharpe(0.05, 2, **kw)
    assert lo < hi
    assert deflated_sharpe(0.0, 10, **kw) < 0.5
    z = 0.05 * np.sqrt(999) / np.sqrt(1 + 0.05 ** 2 * 2 / 4)
    assert np.isclose(deflated_sharpe(0.05, 10, 0.0, 0.0, 3.0, 1000), 0.5 * (1 + __import__("math").erf(z / np.sqrt(2))))


def test_cost_aware_eta_behaviour():
    from mas_trade.v2.smooth import cost_aware_eta
    sig, adv = np.array([0.05, 0.05, 0.05]), np.array([1e8, 1e8, 1e6])
    e = cost_aware_eta(sig, adv, 0.03, CFG)
    assert ((e > 0) & (e < 1)).all() and e[2] < e[0]                           # illiquid -> trade slower
    assert cost_aware_eta(np.array([0.02]), adv[:1], 0.03, CFG) < cost_aware_eta(np.array([0.08]), adv[:1], 0.03, CFG)  # calm -> slower
    free = V2Config(**{**CFG.__dict__, "fee_bps": 0.0, "impact_k": 0.0})
    assert np.allclose(cost_aware_eta(sig, adv, 0.03, free), 1.0)              # no cost -> go straight to target
    assert np.allclose(cost_aware_eta(np.zeros(2), adv[:2], 0.03, free), 1.0)  # no variance, no cost: no 0/0


def test_smooth_reduces_turnover_and_closes_dropped_assets():
    from mas_trade.v2.smooth import cost_aware_smooth
    P = make_panel_synth(n=300)
    bs = build_books(P, CFG, default_v2_agents())
    W = cb.single_book(bs, CFG, 1)
    S = cost_aware_smooth(bs, CFG, W)
    t = lambda X: np.abs(np.diff(X[bs.k0:], axis=0)).sum()
    assert t(S) < t(W)
    for k in range(bs.k0, len(bs.rebal)):
        out = np.setdiff1d(np.arange(W.shape[1]), bs.idx[k])
        assert np.all(S[k, out] == 0)
    assert np.array_equal(S[:bs.k0], W[:bs.k0])


def test_smooth_preserves_target_exposures():
    from mas_trade.v2.smooth import cost_aware_smooth
    P = make_panel_synth(n=300)
    bs = build_books(P, CFG, default_v2_agents())
    for W in (cb.single_book(bs, CFG, 3), cb.single_book(bs, CFG, 4), cb.equal_weight(bs, CFG)):
        S = cost_aware_smooth(bs, CFG, W)
        for k in range(bs.k0, len(bs.rebal)):
            assert np.isclose(S[k].sum(), W[k].sum(), atol=1e-9) and np.isclose(bs.beta[k] @ S[k], bs.beta[k] @ W[k], atol=1e-9)


def test_risk_budget_contributions_proportional_to_budget():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 5)) * rng.uniform(0.5, 2, 5) + 0.6 * rng.normal(size=(500, 1))   # positively correlated books
    Sig = np.cov(X.T)
    for pi in (np.ones(5), np.array([0.4, 0.3, 0.1, 0.1, 0.1])):
        b = cb.risk_budget_weights(Sig, pi)
        rc = b * (Sig @ b)
        assert np.isclose(b.sum(), 1) and (b > 0).all()
        assert np.allclose(rc / rc.sum(), pi / pi.sum(), atol=1e-6)


def test_fixed_share_reduces_to_hedge_and_recovers_after_a_flip():
    rng = np.random.default_rng(1)
    g = rng.normal(0, 1, (60, 3))
    pi0 = cb.fixed_share_budgets(g, 0.0, 0.2)
    ref = np.exp(0.2 * np.cumsum(g, axis=0)); ref /= ref.sum(1, keepdims=True)
    assert np.allclose(pi0[1:], ref[:-1])                       # alpha=0 is plain Hedge (row k uses gains[:k])
    assert np.allclose(cb.fixed_share_budgets(g, 0.1, 0.2).sum(1), 1)
    flip = np.zeros((80, 2)); flip[:40, 0], flip[40:, 1] = 1.0, 1.0   # book 0 good, then book 1 good
    plain, fs = cb.fixed_share_budgets(flip, 0.0, 0.5), cb.fixed_share_budgets(flip, 0.1, 0.5)
    assert fs[60, 1] > plain[60, 1] + 0.05                      # fixed share switches sooner
    assert fs[30].min() >= 0.05 - 1e-12                         # and never starves a book


def test_hedge_params_follow_regime_length():
    a, lr = cb.hedge_params(CFG, 5)
    assert np.isclose(a, CFG.rebal_bars / (CFG.regime_days * CFG.bpd)) and lr > 0


def test_phase2_combiners_hit_target_and_have_no_lookahead():
    P = make_panel_synth(n=300)
    bs1 = build_books(P, CFG, default_v2_agents())
    P2 = make_panel_synth(n=300)
    cut = 200
    P2.R[cut:] = np.random.default_rng(5).normal(0, 0.1, P2.R[cut:].shape)
    bs2 = build_books(P2, CFG, default_v2_agents())
    ks = [k for k, t in enumerate(bs1.rebal) if bs1.k0 <= k and t <= cut]
    for fn in (cb.hedge_only, cb.risk_budget_only, cb.hedge_risk_budget):
        w1, w2 = fn(bs1, CFG), fn(bs2, CFG)
        assert all(np.array_equal(w1[k], w2[k]) for k in ks), fn.__name__
        for k in range(bs1.k0, len(bs1.rebal)):
            ii = bs1.idx[k]
            v = np.sqrt(w1[k, ii] @ bs1.Sig[k] @ w1[k, ii])
            assert abs(v - CFG.target_vol / np.sqrt(P.ppy)) < 1e-9 or np.abs(w1[k]).sum() >= CFG.gross_cap - 1e-9


def test_smooth_books_keeps_neutral_books_neutral_and_timing_on_btc():
    from mas_trade.v2.smooth import smooth_books
    P = make_panel_synth(n=300)
    bs = build_books(P, CFG, default_v2_agents())
    sb = smooth_books(bs, P, CFG)
    t = bs.names.index("Timing")
    for k in range(bs.k0, len(bs.rebal)):
        for a in range(len(bs.names)):
            if a != t:
                assert abs(sb.Wb[k, a].sum()) < 1e-9 and abs(bs.beta[k] @ sb.Wb[k, a]) < 1e-9
        assert np.all(sb.Wb[k, t, 1:] == 0)                       # BTC is column 0: timing never spreads onto alts
    assert np.allclose(sb.pr[: bs.rebal[0]], 0)


def test_risk_budget_stays_positive_and_finite_when_no_exact_solution():
    X = np.random.default_rng(0).normal(size=(200, 5)) @ np.random.default_rng(1).normal(size=(5, 5))
    b = cb.risk_budget_weights(np.cov(X.T), np.ones(5))
    assert np.isfinite(b).all() and (b >= 0).all() and np.isclose(b.sum(), 1)


def test_fusion_coefficients_independent_and_duplicated():
    ic = np.array([0.04, 0.02])
    assert np.allclose(cb.fusion_coefficients(np.eye(2), ic), ic)                       # independent: sum of calibrated views
    R = np.array([[1.0, 0.999], [0.999, 1.0]])                                          # near-duplicate scores
    b = cb.fusion_coefficients(R + 1e-9, np.array([0.03, 0.03]))
    assert np.isclose(b.sum(), 0.03, atol=1e-3) and np.allclose(b[0], b[1])             # the IC is shared, not doubled
    assert cb.fusion_coefficients(np.eye(2), np.array([-0.03, 0.0]))[0] < 0             # a persistently negative IC flips the view


def test_mean_variance_book_neutral_scaled_down_only_and_zero_without_views():
    P = make_panel_synth(n=300)
    bs = build_books(P, CFG, default_v2_agents())
    k = bs.k0 + 2
    ii = bs.idx[k]
    mu = np.zeros(len(P.tickers))
    assert not cb.mean_variance_book(bs, CFG, k, mu).any()
    mu[ii] = np.random.default_rng(0).normal(0, 0.01, len(ii))
    w = cb.mean_variance_book(bs, CFG, k, mu)
    assert abs(w.sum()) < 1e-9 and abs(bs.beta[k] @ w) < 1e-9
    assert np.sqrt(w[ii] @ bs.Sig[k] @ w[ii]) <= CFG.target_vol / np.sqrt(P.ppy) + 1e-12
    w_small = cb.mean_variance_book(bs, CFG, k, mu * 0.01)
    assert np.allclose(w_small, w * 0.01) or np.abs(w_small).sum() < np.abs(w).sum()    # smaller conviction, smaller book


def test_view_fusion_has_no_lookahead_and_finds_planted_signal():
    P = make_panel_synth(n=500, N=20, seed=3)
    rng = np.random.default_rng(3)
    drift = rng.normal(0, 1, 20)
    P.F[:] = (-drift * 1e-4)[None, :] + rng.normal(0, 1e-5, P.F.shape)
    P.R += (drift * 0.002)[None, :]
    bs = build_books(P, CFG, default_v2_agents())
    W = cb.view_fusion(bs, P, CFG)
    late = [k for k in range(bs.k0 + 30, len(bs.rebal)) if bs.idx[k].size]
    corr = np.mean([np.corrcoef(W[k, bs.idx[k]], drift[bs.idx[k]])[0, 1] for k in late])
    assert corr > 0.2                                         # it learned to bet on the carry signal
    P2 = make_panel_synth(n=500, N=20, seed=3)
    P2.R[:] = P.R
    P2.F[:] = P.F
    cut = 350
    P2.R[cut:] = np.random.default_rng(8).normal(0, 0.1, P2.R[cut:].shape)
    bs2 = build_books(P2, CFG, default_v2_agents())
    W2 = cb.view_fusion(bs2, P2, CFG)
    ks = [k for k, t in enumerate(bs.rebal) if bs.k0 <= k and t + CFG.rebal_bars <= cut]
    assert all(np.array_equal(W[k], W2[k]) for k in ks)


def test_diag_risk_model_book_is_neutral_and_differs_from_full_cov():
    P = make_panel_synth(n=300)
    bs = build_books(P, CFG, default_v2_agents())
    k = bs.k0 + 2
    mu = np.zeros(len(P.tickers))
    mu[bs.idx[k]] = np.random.default_rng(0).normal(0, 0.01, len(bs.idx[k]))
    a, b = cb.mean_variance_book(bs, CFG, k, mu, "diag"), cb.mean_variance_book(bs, CFG, k, mu, "lw")
    for w in (a, b):
        assert abs(w.sum()) < 1e-9 and abs(bs.beta[k] @ w) < 1e-9
    assert not np.allclose(a, b)
