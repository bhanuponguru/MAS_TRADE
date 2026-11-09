"""Experiment 023: the final comparison on the dev period, from saved runs only (no engine run).

python final_table.py [--out docs/experiments/data/023]

T1 money and risk (018), T2 centralised against decentralised (019, 020), T3 resilience (021, 022 part B), T4 safety (022 part A),
T5 the deflated Sharpe of the main system with the trial count fixed in docs/experiments/023-final-comparison-on-the-dev-period.md.
Gate C1 checks every shared number against the committed tables of 018-022. The sealed final 12 months are not in any saved run.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew

from mas_trade.diagnostics import deflated_sharpe, read_trials
from mas_trade.metrics import block_bootstrap_sharpe, extended_stats

BPD = {"1d": 1, "4h": 6, "1h": 24}
R = Path("results")
D = Path("docs/experiments/data")
N_H = 45                                              # 15 strategy variants x 3 bar sizes (rules of 023)
T1_RUNS = {"carry": "RankCarry", "H2": "TSMomentum_restricted", "reversal": "RankReversal",
           "market of two": "RankCarry+TSMomentum_restricted", "market of three": "RankCarry+TSMomentum+RankReversal"}


def net(tag):
    return pd.read_csv(R / tag / "bars.csv", index_col=0, parse_dates=True)["net"]


def money(r, ppy):
    st = extended_stats(r, ppy)
    return {"Sharpe": st["Sharpe"], "CAGR": st["CAGR"], "Vol": st["Vol"], "MaxDD": st["MaxDD"], "Calmar": st["Calmar"],
            "final_equity": float((1 + r).prod())}


def t1():
    rows = []
    for bar, bpd in BPD.items():
        ppy = 365.0 * bpd
        nets = {k: net(f"{bar}_broad_{v}") for k, v in T1_RUNS.items()}
        nets["50/50 blend carry+H2"] = 0.5 * nets["carry"] + 0.5 * nets["H2"]
        for k, r in nets.items():
            sh, lo, hi = block_bootstrap_sharpe(r, ppy, 7 * bpd, n_boot=500)
            rows.append({"bar": bar, "run": k, **money(r, ppy), "Sharpe 5%": lo, "Sharpe 95%": hi})
    return pd.DataFrame(rows)


def t2():
    rows = []
    ref3 = net("1d_broad_RankCarry+TSMomentum+RankReversal")
    for name, tag in (("three, hub", "1d_broad_RankCarry+TSMomentum+RankReversal"), ("three, graph complete r1", "1d_broad_three_graph_complete"),
                      ("three, graph line r1", "1d_broad_three_graph_line"), ("three, graph line r3", "1d_broad_three_graph_line_r3")):
        r = net(tag)
        rows.append({"experiment": "019", "run": name, **money(r, 365.0), "equity_vs_hub": float((1 + r).prod() / (1 + ref3).prod() - 1)})
    p20 = pd.read_csv(D / "020/partB_runs.csv")
    tags = {"hub": "020_eight_hub", "complete_r1": "020_eight_complete_r1", "ring_r1": "020_eight_ring_r1", "ring_r3": "020_eight_ring_r3",
            "line_r3": "020_eight_line_r3", "star_r3": "020_eight_star_r3", "hub_cap200": "020_eight_hub_cap200", "ring_r3_cap200": "020_eight_ring_r3_cap200"}
    ref8 = net("020_eight_hub")
    for _, row in p20.iterrows():
        r = net(tags[row["run"]])
        rows.append({"experiment": "020", "run": f"eight, {row['run']}", **money(r, 365.0), "equity_vs_hub": float((1 + r).prod() / (1 + ref8).prod() - 1),
                     "iter_cap": row["iter_cap"], "mean_iterations": row["mean_iterations"], "capped_rebalances": row["capped_rebalances"],
                     "messages_per_rebalance": row["messages_per_rebalance"], "committed_sharpe": row["sharpe"]})
    return pd.DataFrame(rows)


def t3():
    p21 = pd.read_csv(D / "021/partB_runs.csv").set_index("run")
    cases = [("links fail 30%, complete r1", "021_links_complete_r1", "020_eight_hub"),
             ("links fail 30%, ring r3", "021_links_ring_r3", "020_eight_hub"),
             ("RankCarry7 offline May-Aug 2022, complete r1", "021_offline_complete_r1", "021_offline_hub"),
             ("RankCarry7 offline May-Aug 2022, ring r3", "021_offline_ring_r3", "021_offline_hub"),
             ("detector on, no liar, complete r1", "021_detect_clean", "020_eight_hub"),
             ("constant liar + detector, complete r1", "021_liar_detect", "021_liar_hub"),
             ("noise liar May-Jul 2022, no defence", "022_three_liar", "022_three_clean"),
             ("noise liar May-Jul 2022, hold", "022_three_liar_hold", "022_three_clean")]
    rows = []
    for name, tag, ref in cases:
        if not (R / tag / "bars.csv").exists():
            rows.append({"case": name, "run": tag, "reference": ref, "missing": True})
            continue
        r, b = net(tag), net(ref)
        m = money(r, 365.0)
        rows.append({"case": name, "run": tag, "reference": ref, **m, "ref_Sharpe": extended_stats(b, 365.0)["Sharpe"],
                     "equity_vs_ref": float(m["final_equity"] / (1 + b).prod() - 1),
                     "committed_sharpe": p21.loc[tag, "sharpe"] if tag in p21.index else np.nan})
    return pd.DataFrame(rows)


def t4():
    rows = []
    for bar, bpd in BPD.items():
        modes = ("off", "derisk", "hold") if bar == "1d" else ("off", "derisk")
        for mode in modes:
            tag = f"022_{bar}_{mode}"
            rec = pd.read_csv(R / tag / "safety.csv", index_col=0, parse_dates=True)
            rb = pd.read_csv(R / tag / "rebal.csv")
            rows.append({"bar": bar, "safety": mode, **money(net(tag), 365.0 * bpd),
                         **{f"bars_violating_{c}": int((rec[c] < 0).sum()) for c in ("rho_dd", "rho_rvol_recovery", "rho_vol", "rho_solve")},
                         **{f"worst_{c}": float(rec[c].min()) for c in ("rho_dd", "rho_rvol_recovery", "rho_vol", "rho_solve")},
                         "worst_dd365": float(rec["drawdown"].min()), "share_rebalances_vol_ok": float((rec["rho_vol"].dropna() >= 0).mean()),
                         "rebalances_held": int(rb["held"].sum()), "min_dd_scale": float(rb["dd_scale"].min())})
    d = pd.DataFrame(rows)
    off = d[d.safety == "off"].set_index("bar")
    d["Sharpe_vs_off"] = d.Sharpe - d.bar.map(off.Sharpe)
    d["CAGR_vs_off"] = d.CAGR - d.bar.map(off.CAGR)
    return d


def t5():
    tr = read_trials(R / "trials.jsonl")
    strat = tr[tr.name.str.endswith("(vol fix)")].drop_duplicates(["bar", "name"])
    eng = tr[tr.name.str.match(r"^(019|020|021|022) ")]
    n_all = N_H + eng.name.nunique()
    var_ann = float(strat.sharpe_ann.var(ddof=1))
    rows, curve = [], []
    for bar, bpd in BPD.items():
        ppy = 365.0 * bpd
        r = net(f"{bar}_broad_{T1_RUNS['market of two']}").dropna()
        sr = r.mean() / r.std(ddof=1)
        kw = dict(sr_var=var_ann / ppy, skew=float(skew(r)), kurt=float(kurtosis(r, fisher=False)), T=len(r))
        rows.append({"bar": bar, "Sharpe_ann": sr * np.sqrt(ppy), "trials_strategy_logged": int((strat.bar == bar).sum()),
                     "var_trial_sharpe_ann": var_ann, "skew": kw["skew"], "kurtosis": kw["kurt"], "T": kw["T"],
                     "N_h": N_H, "DSR_N_h": deflated_sharpe(sr, N_H, **kw), "N_all": n_all, "DSR_N_all": deflated_sharpe(sr, n_all, **kw),
                     "C2": "PASS" if deflated_sharpe(sr, N_H, **kw) >= 0.95 else "FAIL"})
        curve += [{"bar": bar, "N": n, "DSR": deflated_sharpe(sr, n, **kw)} for n in (1, 2, 5, 10, 20, 45, n_all, 100, 200)]
    return pd.DataFrame(rows), pd.DataFrame(curve)


def c1(T1, T2, T3, T4):
    """Shared numbers against the committed tables of 018-022 (Sharpe to 0.001)."""
    bad = []
    p18 = pd.read_csv(D / "018/runs.csv")
    names = {"carry": "carry", "H2": "H2", "reversal": "reversal", "market of two": "carry+H2", "market of three": "carry+H2+reversal"}
    for _, r in T1[T1.run.isin(names)].iterrows():
        ref = p18[(p18.bar == r.bar) & (p18.run == names[r.run])]
        if len(ref) and abs(ref.Sharpe.iloc[0] - r.Sharpe) > 1e-3:
            bad.append(f"T1 {r.bar} {r.run}: {r.Sharpe:.4f} vs 018 {ref.Sharpe.iloc[0]:.4f}")
    for t, rows in (("T2", T2.dropna(subset=["committed_sharpe"])), ("T3", T3.dropna(subset=["committed_sharpe"]) if "committed_sharpe" in T3 else T3.iloc[:0])):
        for _, r in rows.iterrows():
            if abs(round(r.Sharpe, 3) - r.committed_sharpe) > 1e-3 + 1e-9:
                bad.append(f"{t} {r.run}: {r.Sharpe:.4f} vs committed {r.committed_sharpe}")
    p22 = pd.read_csv(D / "022/runs.csv").set_index("run") if (D / "022/runs.csv").exists() else None
    if p22 is not None:
        for _, r in T4.iterrows():
            tag = f"022_{r.bar}_{r.safety}"
            if tag in p22.index and abs(p22.loc[tag, "sharpe"] - r.Sharpe) > 1e-3:
                bad.append(f"T4 {tag}: {r.Sharpe:.4f} vs 022 {p22.loc[tag, 'sharpe']}")
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/experiments/data/023")
    args = ap.parse_args()
    T1, T2, T3, T4 = t1(), t2(), t3(), t4()
    T5, curve = t5()
    pd.options.display.width = 250
    pd.options.display.float_format = "{:.4f}".format
    for name, t in (("T1 money and risk", T1), ("T2 centralised against decentralised", T2), ("T3 resilience", T3), ("T4 safety", T4),
                    ("T5 deflated Sharpe of the market of two", T5), ("T5 curve", curve.pivot(index="N", columns="bar", values="DSR"))):
        print(f"\n{name}\n{t.to_string()}")
    bad = c1(T1, T2, T3, T4)
    print("\nC1 consistency with 018-022: " + ("PASS" if not bad else "FAIL\n  " + "\n  ".join(bad)))
    print("C2 deflated Sharpe >= 0.95 at N_h: " + ", ".join(f"{r.bar} {r.C2}" for r in T5.itertuples()))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, t in (("T1_money", T1), ("T2_consensus", T2), ("T3_resilience", T3), ("T4_safety", T4), ("T5_deflated_sharpe", T5), ("T5_curve", curve)):
        t.round(5).to_csv(out / f"{name}.csv", index=False)
