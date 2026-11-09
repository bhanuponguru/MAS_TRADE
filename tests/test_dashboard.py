"""The dashboard's data layer (decision 0045), and the app itself when the dashboard dependency group is installed."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mas_trade import dashboard_data as dd


def test_simulate_reaches_the_central_optimum_and_isolates_a_liar():
    r = dd.simulate(M=6, topology="complete", seed=0, tol=1e-7)
    assert r["converged"] and r["final_error"] < 1e-4 and len(r["error"]) == r["iterations"] == len(r["disagreement"])
    assert r["messages"] == r["iterations"] * 2 * 15
    liar = dd.simulate(M=6, topology="complete", liar="constant", size=0.01, detect=50, seed=0, tol=1e-7)
    assert liar["isolated"] == [3] and liar["converged"] and liar["final_error"] < 1e-4


def test_agent_wealth_and_stats():
    idx = pd.date_range("2021-01-01", periods=4)
    bars = pd.DataFrame({"net": [0.0, 0.01, -0.02, 0.01], "acc_A": [0.0, 0.01, 0.0, 0.0], "acc_B": [0.0, 0.0, -0.02, 0.01]}, index=idx)
    w = dd.agent_wealth(bars)
    assert list(w.columns) == ["A", "B"] and np.isclose(w.iloc[-1].sum(), 1.0 + bars.net.sum())
    s = dd.stats(bars.net, 365.0)
    assert np.isclose(s["Final equity"], (1 + bars.net).prod()) and s["MaxDD"] < 0
    assert dd.bar_of("022_4h_off") == "4h" and dd.bar_of("1h_broad_RankCarry") == "1h" and dd.bar_of("020_eight_hub") == "1d"


def test_app_runs_without_errors():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).parents[1] / "dashboard.py"), default_timeout=300).run()
    assert not at.exception and len(at.tabs) == 6
    assert dict((m.label, m.value) for m in at.metric)["converged"] == "yes"
