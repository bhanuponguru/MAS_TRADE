import numpy as np

from mas_trade.funding import CAP, INTEREST, ar1_coefficient, forecast_funding_sum, funding_rate


def test_funding_is_the_flat_interest_inside_the_band_and_follows_the_premium_outside():
    p = np.array([-0.0003, 0.0, 0.0002, 0.0004, 0.0008, -0.0008])
    f = funding_rate(p)
    assert np.allclose(f[:4], INTEREST)                       # |I - P| <= c: the flat 0.01% rate
    assert np.isclose(f[4], 0.0008 - CAP) and np.isclose(f[5], -0.0008 + CAP)


def test_forecast_of_a_constant_premium_is_the_formula_times_the_hours():
    prem = np.full((900, 3), 0.0)
    prem[:, 1] = 0.0008
    prem[:, 2] = -0.0008
    f = forecast_funding_sum(prem, horizon_hours=48)
    assert np.allclose(f, funding_rate(np.array([0.0, 0.0008, -0.0008])) / 8 * 48)


def test_forecast_reverts_toward_the_trailing_mean_at_the_estimated_speed():
    rng = np.random.default_rng(0)
    T, n, phi = 3000, 20, 0.9
    x = np.zeros((T, n))
    for t in range(1, T):
        x[t] = phi * x[t - 1] + rng.normal(0, 1e-4, n)
    assert abs(ar1_coefficient(x) - phi) < 0.02
    x[-1] = 0.0015                                            # a spike in the latest hour
    short = forecast_funding_sum(x, 4)
    long = forecast_funding_sum(x, 240)
    assert (short / 4 > long / 240).all()                     # the spike matters near, and decays


def test_forecast_uses_only_the_window_it_is_given_and_handles_missing_coins():
    rng = np.random.default_rng(1)
    prem = rng.normal(0, 3e-4, (800, 4))
    prem[:, 3] = np.nan
    f = forecast_funding_sum(prem, 24)
    assert np.isfinite(f[:3]).all() and np.isnan(f[3])
    prem2 = prem.copy()
    prem2[:300] = 0.5                                         # the far past, outside the 720-hour mean window
    assert np.allclose(forecast_funding_sum(prem2[300:], 24), forecast_funding_sum(prem[300:], 24), equal_nan=True)
