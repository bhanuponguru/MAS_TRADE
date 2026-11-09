"""Interactive dashboard of the multi-agent trading system (decision 0045; proposal section 4).

uv run --group dashboard streamlit run dashboard.py

Tabs: the consensus simulator (the real decentralised optimiser, live, on a simulated problem), topology and communication
(experiment 020), performance and the agents' wealth (saved runs), the STL safety record (experiment 022), resilience (021, 022)
and the final comparison (023). Saved runs are read from results/ (local, gitignored); the committed tables from
docs/experiments/data/. Dev period only: no saved run contains the sealed final 12 months.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mas_trade import dashboard_data as dd
from mas_trade.graph_admm import TOPOLOGIES

st.set_page_config(page_title="MAS trade dashboard", layout="wide")
st.title("Resilient decentralised portfolio consensus")
st.caption("Agents (trading hypotheses) coordinate one portfolio by ADMM over a communication graph, under STL safety specs. "
           "Binance USD-M perpetuals, dev period only (the final 12 months are sealed).")

tabs = st.tabs(["Consensus simulator", "Topology & communication", "Performance & agents", "STL safety", "Resilience", "Final comparison"])
COLORS = {"honest": "#2b6cb0", "liar": "#c53030", "isolated": "#a0aec0"}


def graph_figure(A, faulty, isolated):
    M = len(A)
    xy = dd.circle_layout(M)
    fig = go.Figure()
    ex, ey = [], []
    for i in range(M):
        for j in range(i + 1, M):
            if A[i, j]:
                ex += [xy[i, 0], xy[j, 0], None]
                ey += [xy[i, 1], xy[j, 1], None]
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="#cbd5e0", width=1.5), hoverinfo="skip", showlegend=False))
    col = [COLORS["isolated"] if i in isolated else COLORS["liar"] if i in faulty else COLORS["honest"] for i in range(M)]
    lab = [f"agent {i}" + (" (liar, isolated)" if i in isolated and i in faulty else " (isolated)" if i in isolated
                           else " (liar)" if i in faulty else "") for i in range(M)]
    fig.add_trace(go.Scatter(x=xy[:, 0], y=xy[:, 1], mode="markers+text", text=[str(i) for i in range(M)], textfont=dict(color="white"),
                             marker=dict(size=34, color=col, line=dict(color="white", width=2)), hovertext=lab, hoverinfo="text",
                             showlegend=False))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
                      plot_bgcolor="rgba(0,0,0,0)")
    return fig


@st.cache_data(show_spinner=False)
def run_sim(M, topology, rounds, link_fail, liar, size, detect, seed, iters):
    return dd.simulate(M=M, topology=topology, rounds=rounds, link_fail=link_fail, liar=liar, size=size, detect=detect, seed=seed, iters=iters)


# ---------------------------------------------------------------- 1. consensus simulator
with tabs[0]:
    st.subheader("Live: agents agree on one portfolio by talking only to their neighbours")
    st.markdown("Each agent solves its own part of the portfolio problem, keeps its own estimate of the group's average position "
                "and of the prices of the shared limits, and mixes them with its neighbours (dynamic average consensus, Metropolis "
                "weights). The central (hub) optimum is the reference. Problem: simulated, every limit binding (experiments 020-021).")
    c = st.columns(4)
    M = c[0].slider("agents", 4, 16, 8, step=1)
    topology = c[0].selectbox("network", [t for t in TOPOLOGIES if t != "random"] + ["ring2", "random"], index=0)
    rounds = c[1].slider("gossip rounds per iteration", 1, 5, 1)
    link_fail = c[1].slider("share of links down each round", 0.0, 0.6, 0.0, 0.05)
    liar = c[2].selectbox("misbehaving agent 3", ["none", "constant lie", "noise"], index=0)
    size = c[2].select_slider("size of the lie", [0.001, 0.01, 0.1, 1.0], value=0.01)
    detect = c[3].checkbox("detect and isolate (W-MSR test)", value=False)
    seed = c[3].number_input("problem seed", 0, 20, 0)
    kind = {"none": None, "constant lie": "constant", "noise": "noise"}[liar]
    iters = 300 if (kind == "noise" and not detect) else 3000          # an undefended noise liar diverges (experiment 022)
    with st.spinner("solving..."):
        r = run_sim(M, topology, rounds, link_fail, kind, size, 50 if detect else 0, int(seed), iters)
    left, right = st.columns([1, 2])
    with left:
        st.plotly_chart(graph_figure(r["A"], r["faulty"], r["isolated"]), width="stretch")
        st.caption("blue honest, red the liar, grey isolated")
    with right:
        fig = go.Figure()
        k = np.arange(1, len(r["error"]) + 1)
        fig.add_trace(go.Scatter(x=k, y=np.maximum(r["error"], 1e-12), name="error vs central optimum"))
        fig.add_trace(go.Scatter(x=k, y=np.maximum(r["disagreement"], 1e-12), name="disagreement between agents"))
        fig.update_layout(height=380, yaxis_type="log", xaxis_title="ADMM iteration", yaxis_title="relative size (log)",
                          margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig, width="stretch")
    m = st.columns(5)
    m[0].metric("iterations", r["iterations"])
    m[1].metric("converged", "yes" if r["converged"] else "no")
    m[2].metric("final error", f"{r['final_error']:.1e}")
    m[3].metric("messages", f"{r['messages']:,}")
    m[4].metric("isolated", ", ".join(map(str, r["isolated"])) or "none")
    if r["failure"]:
        st.error(f"{r['failure']}: the graph is not robust enough for the detector (a plain ring; experiment 021, A3). Try 'ring2'.")
    elif kind and not detect:
        st.warning("No defence: the lie corrupts the agreed portfolio (error stays large). Turn on detect-and-isolate, "
                   "or see the 'hold' supervisor in the STL safety tab.")

# ---------------------------------------------------------------- 2. topology and communication
with tabs[1]:
    st.subheader("Network shape changes the communication needed, not the answer (experiment 020)")
    s = dd.committed("020", "partA_summary.csv")
    if s is not None:
        Ms = sorted(s.M.unique())
        Msel = st.radio("agents", Ms, index=Ms.index(8) if 8 in Ms else 0, horizontal=True)
        t = s[s.M == Msel]
        c1, c2 = st.columns(2)
        for col, y, title in ((c1, "iters", "median iterations to converge"), (c2, "messages", "messages per solve")):
            fig = go.Figure()
            for rr in sorted(t.rounds.unique()):
                u = t[t.rounds == rr]
                fig.add_trace(go.Bar(x=u.topology, y=u[y], name=f"{rr} round(s)"))
            fig.update_layout(title=title, barmode="group", height=360, margin=dict(l=10, r=10, t=40, b=10))
            col.plotly_chart(fig, width="stretch")
        st.dataframe(t, width="stretch", hide_index=True)
    b = dd.committed("020", "partB_runs.csv")
    if b is not None:
        st.markdown("**On real data (eight agents, 1d):** every shape gives the hub's result; sparse shapes hit the iteration cap more often.")
        st.dataframe(b, width="stretch", hide_index=True)

# ---------------------------------------------------------------- 3. performance and agents
runs = dd.saved_runs()
with tabs[2]:
    st.subheader("Money and the agents' wealth (saved runs, dev period)")
    if not runs:
        st.info("No saved runs in results/ on this machine (they are gitignored); see the committed tables in the other tabs.")
    else:
        default = [x for x in ("1d_broad_RankCarry+TSMomentum_restricted", "1d_broad_RankCarry", "1d_broad_three_graph_complete") if x in runs]
        sel = st.multiselect("runs", runs, default=default)
        if sel:
            fig = go.Figure()
            rows = []
            for tag in sel:
                bars, _, _ = dd.load_run(tag)
                fig.add_trace(go.Scatter(x=bars.index, y=dd.equity(bars), name=tag))
                rows.append({"run": tag, **dd.stats(bars["net"], dd.PPY[dd.bar_of(tag)])})
            fig.update_layout(height=420, yaxis_type="log", yaxis_title="equity (start = 1, log)", margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig, width="stretch")
            st.dataframe(pd.DataFrame(rows).round(3), width="stretch", hide_index=True)
            one = st.selectbox("agents' wealth in run", sel)
            bars, _, _ = dd.load_run(one)
            w = dd.agent_wealth(bars)
            if w.shape[1] > 1:
                fig = go.Figure()
                for a in w.columns:
                    fig.add_trace(go.Scatter(x=w.index, y=w[a], name=a, stackgroup="one"))
                fig.update_layout(height=360, yaxis_title="wealth (units of initial equity)", margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, width="stretch")
                st.caption("The wealth-staked market: each agent bets its own wealth and keeps its own P&L, so a losing agent's "
                           "capital shrinks (reversal in the market of three).")

# ---------------------------------------------------------------- 4. STL safety
with tabs[3]:
    st.subheader("STL safety record: robustness of each spec over time (> 0 satisfied; experiment 022, decision 0044)")
    safe = [r_ for r_ in runs if (dd.RESULTS / r_ / "safety.csv").exists()]
    if not safe:
        st.info("No saved run with a safety record on this machine; see the committed table below.")
    else:
        tag = st.selectbox("run", safe, index=safe.index("022_1d_derisk") if "022_1d_derisk" in safe else 0)
        compare = st.selectbox("compare with", ["(none)"] + safe, index=(["(none)"] + safe).index("022_1d_off") if "022_1d_off" in safe else 0)
        specs = {"rho_dd": "drawdown (365-day DD >= -15%)", "rho_rvol_recovery": "realised vol 30d <= 40%, recovered within 14 days",
                 "rho_vol": "ex-ante vol <= 1.05 x target", "rho_solve": "solver health (converged or residual <= 1e-3)"}
        spec = st.radio("spec", list(specs), format_func=specs.get, horizontal=True)
        fig = go.Figure()
        for t_ in [tag] + ([compare] if compare != "(none)" else []):
            _, rebal, sf = dd.load_run(t_)
            y = sf[spec].dropna()
            fig.add_trace(go.Scatter(x=y.index, y=y.clip(lower=-1.0), name=t_, mode="lines" if spec in ("rho_dd", "rho_rvol_recovery") else "markers"))
        for name, (a, b_) in dd.STRESS.items():
            fig.add_vrect(x0=a, x1=b_, fillcolor="#fed7d7", opacity=0.4, line_width=0, annotation_text=name, annotation_position="top left")
        fig.add_hline(y=0, line_color="#c53030", line_dash="dash")
        fig.update_layout(height=420, yaxis_title="robustness (clipped at -1)", margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")
        _, rebal, sf = dd.load_run(tag)
        c1, c2 = st.columns(2)
        if rebal is not None and "dd_scale" in rebal:
            fig = go.Figure(go.Scatter(x=rebal.date, y=rebal.dd_scale, mode="lines+markers", name="vol multiplier"))
            fig.update_layout(title="derisk: volatility-target multiplier", height=300, margin=dict(l=10, r=10, t=40, b=10), yaxis_range=[0, 1.05])
            c1.plotly_chart(fig, width="stretch")
            held = rebal[rebal.held.astype(bool)] if "held" in rebal else rebal.iloc[:0]
            fig = go.Figure(go.Scatter(x=rebal.date, y=rebal.rel_res.clip(lower=1e-9), mode="markers", name="relative residual",
                                       marker=dict(color=np.where(rebal.get("held", False).astype(bool), COLORS["liar"], COLORS["honest"]))))
            fig.add_hline(y=1e-3, line_dash="dash", line_color="#c53030")
            fig.update_layout(title=f"solver residual per rebalance (red = held, {len(held)} held)", height=300, yaxis_type="log",
                              margin=dict(l=10, r=10, t=40, b=10))
            c2.plotly_chart(fig, width="stretch")
    w = dd.committed("022", "windows.csv")
    if w is not None:
        st.markdown("**Stress windows, all runs of experiment 022**")
        st.dataframe(w, width="stretch", hide_index=True)

# ---------------------------------------------------------------- 5. resilience
with tabs[4]:
    st.subheader("Link failures, an offline agent, a liar (experiments 021, 022)")
    a = dd.committed("021", "partA.csv")
    if a is not None:
        st.markdown("**Simulated problems (eight agents):** error of the agreed portfolio against the right answer.")
        st.dataframe(a.groupby(["case", "graph", "liar", "size", "defence"], dropna=False)
                     .agg(runs=("seed", "size"), converged=("converged", "mean"), worst_error=("net_error", "max"),
                          liar_isolated=("liar_isolated", "mean"), honest_isolated=("honest_isolated", "mean")).reset_index(),
                     width="stretch", hide_index=True)
    b = dd.committed("021", "partB_runs.csv")
    if b is not None:
        st.markdown("**Real data (1d):** each failure against its correct reference.")
        st.dataframe(b, width="stretch", hide_index=True)
    r22 = dd.committed("022", "runs.csv")
    if r22 is not None:
        st.markdown("**Stealthy noise liar and the hold supervisor (022 part B)** and the safety modes (part A).")
        st.dataframe(r22, width="stretch", hide_index=True)

# ---------------------------------------------------------------- 6. final comparison
with tabs[5]:
    st.subheader("Final comparison on the dev period (experiment 023)")
    names = {"T1_money.csv": "Money and risk per agent and market", "T2_consensus.csv": "Centralised against decentralised",
             "T3_resilience.csv": "Resilience against references", "T4_safety.csv": "Safety modes", "T5_deflated_sharpe.csv": "Deflated Sharpe"}
    found = False
    for f, title in names.items():
        t = dd.committed("023", f)
        if t is not None:
            found = True
            st.markdown(f"**{title}**")
            st.dataframe(t.round(4), width="stretch", hide_index=True)
    if not found:
        st.info("Experiment 023 has not been computed yet (uv run python final_table.py).")
