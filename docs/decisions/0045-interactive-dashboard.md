# 0045. Interactive dashboard for the final demonstration

Status: **Accepted**   Date: 2026-11-09   Where: `dashboard.py`, `mas_trade/dashboard_data.py`, `pyproject.toml` (dependency group `dashboard`: streamlit, plotly)   Evidence: `tests/test_dashboard.py`

## Context
The proposal (section 4) promises that the final demonstration is supported by an interactive simulation dashboard that shows the agent communication network, the evolution of consensus, the optimisation behaviour, portfolio performance and the evolution of the formal safety measures. Experiments 019-022 produced all of these as saved runs and committed tables, but only as files.

## Options
1. Static figures in the report (matplotlib). No interaction; the network and consensus cannot be explored.
2. A static web page with the data embedded. Interactive charts, but the consensus could only be replayed, not re-run with other settings.
3. **A local Streamlit app** that reads the saved runs and committed tables and also runs the real decentralised optimiser live on a simulated problem, so the network shape, gossip rounds, link failures and a liar (with or without detect-and-isolate) can be changed during the demonstration.

## Decision
Option 3. `uv run --group dashboard streamlit run dashboard.py`. Six tabs: consensus simulator (live `graph_admm` on the simulated problems of experiments 020-021: graph, error against the central optimum and disagreement per iteration, messages, who was isolated), topology and communication (020), performance and the agents' wealth (saved runs), the STL safety record with the stress windows (022), resilience (021, 022) and the final comparison (023). The data and simulation code lives in `mas_trade/dashboard_data.py` (tested without Streamlit); the app only draws. Streamlit and Plotly are an optional dependency group, so the core and the tests do not need them (the app test is skipped without them).

## Consequences
- The demonstration shows the mechanisms live; nothing in it changes a result (it only reads saved runs, and the live simulator uses simulated problems, never market data).
- The saved runs in `results/` are local and gitignored; on another machine those tabs show the committed tables only until the runs are reproduced.
- An undefended noise liar is capped at 300 iterations in the simulator, because its solve diverges and slows down (experiment 022, amendment 1).
- No sealed data: no saved run contains the final 12 months.

## Rollback
Delete `dashboard.py`, `mas_trade/dashboard_data.py`, `tests/test_dashboard.py` and the `dashboard` dependency group; nothing else depends on them.
