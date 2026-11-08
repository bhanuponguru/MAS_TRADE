"""STL safety monitor and supervisor of the system (decision 0044, experiment 022).

Monitor (reporting, no effect on trading): per-bar robustness of the system specs, from the run's traces.
    phi_vol    at every rebalance, ex-ante volatility <= 1.05 x the volatility target in force
    phi_dd     drawdown from the peak of the last dd_days >= -dd_limit                         (mandate 0026: 15% over 365 days)
    phi_rvol   G (realised 30-day volatility <= 2 x target  ->  recovered within 14 days)       (0026: 40% crypto vol, 14 days)
    phi_solve  at every rebalance, the solve converged or its relative residual <= hold_tol
Robustness > 0 means satisfied (stl.py semantics: margin normalised by the limit).

Supervisor (behind EngineConfig.safety, default "off"):
    derisk  the volatility target is multiplied by stl.kelly_scale(margin of phi_dd): 1 while at least half of the drawdown
            budget is left, falling linearly to 0.2 at the limit (de-risk before the limit, not after; 0026's buffer and floor).
            The drawdown uses only bars before the rebalance.
    hold    a rebalance whose solve is unsafe (not converged, relative residual above hold_tol) trades nothing: the drifted
            positions are kept. The defence against a misbehaving agent that is not detected (experiment 021).
"""
import numpy as np
import pandas as pd

from . import stl


def drawdown_scale(net_past, cfg):
    """Multiplier of the volatility target at a rebalance, from the net returns of the bars before it."""
    wb = max(int(round(cfg.dd_days * cfg.bpd)), 1)
    r = np.asarray(net_past, float)[-wb:]
    if not len(r):
        return 1.0
    dd = float(stl.rolling_drawdown(r, wb)[-1])
    return float(stl.kelly_scale(stl.ge(dd, -cfg.dd_limit), cfg.safety_buffer, cfg.safety_min_scale))


def unsafe(sol, cfg):
    return (not sol.converged) and sol.state.get("rel_res", np.inf) > cfg.hold_tol


def safety_record(res, cfg):
    """Per-bar robustness of the monitor's specs (DataFrame indexed by date). Rebalance-only specs are NaN between rebalances."""
    ppy, bpd = cfg.ppy, cfg.bpd
    net = pd.Series(res.net, index=res.dates)
    dd = stl.rolling_drawdown(net.values, int(round(cfg.dd_days * bpd)))
    rvol = stl.rolling_vol(net.values, int(round(30 * bpd)), ppy)
    rho_rvol = stl.le(np.nan_to_num(rvol, nan=0.0), 2.0 * cfg.target_vol)
    rec = stl.recovery(rho_rvol, int(round(14 * bpd)))
    out = pd.DataFrame({"net": net.values, "drawdown": dd, "rho_dd": stl.ge(dd, -cfg.dd_limit), "rvol30": rvol,
                        "rho_rvol": rho_rvol, "rho_rvol_recovery": rec}, index=res.dates)
    reb_dates = pd.DatetimeIndex(res.solve_dates)
    for c in ("rho_vol", "rho_solve", "dd_scale", "held"):
        out[c] = np.nan
    lim = 1.05 * cfg.target_vol * np.asarray(res.dd_scale)              # the target in force at each rebalance
    out.loc[reb_dates, "rho_vol"] = (lim - np.asarray(res.sys_vol)) / lim
    rr = np.asarray(res.rel_res)
    conv = np.asarray(res.converged, bool)
    out.loc[reb_dates, "rho_solve"] = np.where(conv, 1.0, stl.le(rr, cfg.hold_tol))
    out.loc[reb_dates, "dd_scale"] = res.dd_scale
    out.loc[reb_dates, "held"] = np.asarray(res.held, float)
    return out


WINDOWS = {"may2021": ("2021-05-01", "2021-07-31"), "luna2022": ("2022-05-01", "2022-07-31"),
           "ftx2022": ("2022-11-01", "2023-01-31")}


def window_summary(rec, windows=WINDOWS, ppy=365.0):
    """Per stress window: return, worst drawdown inside the window (from the window's own start), realised volatility, the
    lowest robustness of each spec and the bars that violate it."""
    rows = {}
    for name, (a, b) in list(windows.items()) + [("whole", (str(rec.index[0].date()), str(rec.index[-1].date())))]:
        w = rec.loc[a:b]
        if not len(w):
            continue
        eq = (1 + w.net).cumprod()
        rows[name] = {"return": float(eq.iloc[-1] - 1), "max_dd_in_window": float((eq / eq.cummax() - 1).min()),
                      "vol": float(w.net.std() * np.sqrt(ppy)),
                      **{f"min_{c}": float(w[c].min()) for c in ("rho_dd", "rho_rvol_recovery", "rho_vol", "rho_solve")},
                      **{f"bars_violating_{c}": int((w[c] < 0).sum()) for c in ("rho_dd", "rho_rvol_recovery", "rho_vol", "rho_solve")},
                      "min_dd_scale": float(w.dd_scale.min()), "rebalances_held": int(np.nansum(w.held))}
    return pd.DataFrame(rows).T
