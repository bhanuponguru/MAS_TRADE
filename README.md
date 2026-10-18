# MAS_Trade

Multi-agent consensus portfolio optimisation, built from the AI3403 MAS course material in `references/`.

```
uv sync
uv run python run_backtest.py              # downloads prices once -> data/prices.csv; results/ (--mode admm for ADMM)
uv run python run_adversary_experiment.py  # plain consensus vs W-MSR with one compromised agent
uv run pytest
```

Per rebalance (every 21 days, using only past returns):
1. Each agent forecasts expected returns `mu`, portfolio `w = mu / sum|mu|` (+ long, - short).
2. Trust `s_i = Phi(m_i*sqrt(H)/sd_i)`: forecast probability that agent i is profitable, from the EWMA mean/std of its standalone track record.
3. Consensus matrix `W_ij = a_ij s_j / sum_l a_il s_l`. Agents run K rounds of W-MSR consensus, pinned to their own strategy with weight `b`.
4. Capital moves between agents as `c <- (1-eta) c + eta W^T c` (conserves total, flows toward high trust), then each agent trades its portfolio with its own capital.

Settings live in `mas_trade/config.py`. Outputs: `results/*.png`, `results/metrics.csv`.
