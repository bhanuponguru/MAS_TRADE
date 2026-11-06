import numpy as np

from mas_trade.agents.averaging import fuse, inverse_mse_weights, stacking_weights
from mas_trade.stl import belief_bound

N, M, TW = 60, 5, 250                       # coins, members, periods of history behind the weights
SIGMA_ALPHA, SIGMA_EPS = 0.005, 0.06


def _members(rng, s2, n_periods):
    alpha = rng.normal(0, SIGMA_ALPHA, (n_periods, N))
    r = alpha + rng.normal(0, SIGMA_EPS, (n_periods, N))
    b = alpha[None] + rng.normal(size=(len(s2), n_periods, N)) * np.sqrt(s2)[:, None, None]
    return alpha, r, b


def _corr(x, y):
    return float(np.corrcoef(x.ravel(), y.ravel())[0, 1])


def _compare(s2, seeds=20):
    gain = []
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        alpha, r, b = _members(rng, s2, TW + 1)
        hist_b, hist_r = b[:, :TW].reshape(len(s2), -1).T, r[:TW].ravel()
        w = stacking_weights(hist_b, hist_r)
        now = b[:, TW]
        gain.append((_corr(fuse(now, w), alpha[TW]), _corr(fuse(now), alpha[TW])))
    g = np.array(gain)
    return g[:, 0].mean(), g[:, 1].mean()


def test_a1_stacking_beats_equal_weights_when_member_errors_differ():
    s0 = SIGMA_ALPHA ** 2
    stacked, equal = _compare(np.array([1, 1, 4, 4, 4]) * s0)
    assert stacked > equal


def test_a1_stacking_is_not_worse_when_members_are_equal():
    s0 = SIGMA_ALPHA ** 2
    stacked, equal = _compare(np.full(M, 2.0) * s0)
    assert stacked >= 0.98 * equal


def test_a1_regression_weights_are_less_noisy_than_inverse_mse_weights():
    s0 = SIGMA_ALPHA ** 2
    s2 = np.array([1, 1, 4, 4, 4]) * s0
    target = (1 / s2) / (1 / s2).sum()
    err_stack, err_mse = [], []
    for seed in range(20):
        _, r, b = _members(np.random.default_rng(seed), s2, TW)
        hb, hr = b.reshape(M, -1).T, r.ravel()
        err_stack.append(np.abs(stacking_weights(hb, hr, shrink=0.0) - target).sum())
        err_mse.append(np.abs(inverse_mse_weights(hb, hr, shrink=0.0) - target).sum())
    assert np.mean(err_stack) < np.mean(err_mse)


def test_a2_sanity_guard_contains_an_exploding_member():
    rng = np.random.default_rng(3)
    history = rng.normal(0, 0.003, (200, N)) + rng.normal(0, 0.005, (200, N))
    bound = belief_bound(history)
    ch_guard, ch_trim, ch_plain = [], [], []
    for _ in range(20):
        b = rng.normal(0, 0.003, (8, N)) + rng.normal(0, 0.005, N)[None]
        bad = b.copy()
        bad[rng.integers(8)] *= 100
        rel = lambda x, y: np.linalg.norm(x - y) / np.linalg.norm(y)
        k = int(np.argmax(np.abs(bad).max(1)))                              # the injected member
        honest = np.delete(b, k, axis=0)
        ch_guard.append(rel(fuse(bad, bound=bound), fuse(honest)))          # guard on: equals the honest members' average
        ch_trim.append(rel(fuse(bad, trim=1), fuse(b, trim=1)))
        ch_plain.append(rel(fuse(bad), fuse(b)))
    assert np.max(ch_guard) < 1e-12                     # the fault is excluded entirely (see experiment 012 for the criterion change)
    assert np.mean(ch_plain) > 1.0                      # without a guard the fault dominates
    assert np.mean(ch_trim) < 0.2 * np.mean(ch_plain)   # trim = 1 alone helps a lot but misses the 10% bar (about 13%)
    assert np.mean(ch_trim) > 0.10


def test_sanity_guard_leaves_honest_members_untouched_and_drops_nan():
    b = np.array([[0.001, -0.002, 0.003], [0.002, 0.001, -0.001], [np.nan, 5.0, 0.0]])
    f = fuse(b, bound=0.01)
    assert np.allclose(f, [(0.001 + 0.002) / 2, (-0.002 + 0.001) / 2, (0.003 - 0.001) / 2])     # the corrupt third member is out everywhere
    one_bad_coin = np.array([[0.001, 0.002, 0.003, 0.004] * 5, [0.002, 0.001, 0.0, 0.001] * 5, [0.0015, 0.0015, 5.0, 0.0015] * 5])
    g = fuse(one_bad_coin, bound=0.01, max_bad_share=0.3)                                        # 5 of 20 coins bad: coin-wise exclusion only
    assert np.isclose(g[2], (0.003 + 0.0) / 2) and np.isclose(g[0], (0.001 + 0.002 + 0.0015) / 3)


def test_fuse_weights_and_trim_behave():
    b = np.array([[1.0, 2.0], [3.0, 4.0], [100.0, -50.0]])
    assert np.allclose(fuse(b[:2], [0.25, 0.75]), [2.5, 3.5])
    assert np.allclose(fuse(b, trim=1), [3.0, 2.0])
