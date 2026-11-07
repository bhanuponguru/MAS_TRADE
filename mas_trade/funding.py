"""The mechanical part of carry: forecast the funding a long will pay from the premium index.

Binance funding per event is F = P + clamp(I - P, +-c), with P the time-weighted average premium over the interval, I = 0.01%
per 8 hours and c = 0.05% (experiment 011). Inside +-c of I the funding is the flat interest rate; outside it follows the
premium, so the cross-section of funding is driven by the coins whose premium leaves that band. The forecast projects the
hourly premium forward with an AR(1) around the coin's own trailing mean and maps it through the formula.
"""
import warnings

import numpy as np

INTEREST = 1e-4        # per 8-hour interval
CAP = 5e-4
EVENT_HOURS = 8


def funding_rate(p, interest=INTEREST, cap=CAP):
    """Funding per 8-hour event for an interval premium p."""
    return p + np.clip(interest - p, -cap, cap)


def _nanmean(x, axis=0, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)      # a coin with no data at all gives NaN, which is meant
        return np.nanmean(x, axis=axis, **kw)


def ar1_coefficient(prem):
    """Pooled hourly AR(1) coefficient of the premium around each coin's own mean (prem: (T, n), NaN allowed)."""
    x = prem - _nanmean(prem, axis=0, keepdims=True)
    a, b = x[1:], x[:-1]
    ok = np.isfinite(a) & np.isfinite(b)
    den = (b[ok] ** 2).sum()
    return float(np.clip((a[ok] * b[ok]).sum() / den, 0.0, 0.9999)) if den > 0 else 0.0


def forecast_funding_sum(prem, horizon_hours, mean_hours=720):
    """prem: (T, n) hourly premium before the decision (last row = the latest hour). Returns (n,) the forecast of the funding
    paid by a long per unit notional over the next `horizon_hours` (NaN where the premium is missing)."""
    mu = _nanmean(prem[-mean_hours:], axis=0)
    p0 = prem[-1]
    phi = ar1_coefficient(prem)
    h = np.arange(horizon_hours)[:, None]
    path = mu[None, :] + phi ** h * (p0 - mu)[None, :]
    return (funding_rate(path) / EVENT_HOURS).sum(0)
