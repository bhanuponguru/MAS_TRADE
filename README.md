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

## Hierarchy (level 2)
With `Config(hierarchical=True)` each strategy's capital `c_i` is split over one subagent per asset, `G[i,k]` (row sums = `c_i`). After the strategy-level reallocation, subagents inside each strategy reallocate by the same rule, `g <- (1-eta_sub) g + eta_sub W^T g`, with `W_kl ~ a_kl s_il` and subagent trust `s_ik = P(bet on k pays off) * P(subagent profitable in the past)`. The side of each position is the sign of the post-consensus weight. `run_backtest.py` reports it as `MAS-H`; `run_adversary_experiment.py --hier` repeats the attack test.

## Crypto perps (24/7)
`uv run python download_crypto_data.py` downloads Binance USD-M perpetual klines (1d/4h/1h) and funding for a point-in-time, survivorship-free top-50 universe (data/crypto/, ~350 MB). `crypto_data.load_panel(bar)` returns returns, eligibility, funding and the BTC benchmark for `run_backtest`; `Config.for_tier("1h")` sets lookbacks/rebalance/annualisation in time units.
`uv run python run_crypto_benchmark.py --bar 1h --universe broad --eval-from 2022-01-13` runs the benchmark for one bar size (BTC, equal-weight, naive average, each agent, MAS and MAS-H; dev/holdout split, gross vs net, per-year returns, paired bootstrap vs BTC) into `results/crypto/`. `--universe majors` is the stricter top-20, 365-day-history universe.


## v2: absolute-return benchmark (crypto perps)

`uv run python run_v2_benchmark.py --bar 1d --universe broad --smooth` (also 4h, 1h). Agents: XS momentum, residual reversal, funding carry, size/liquidity (neutral books) and a BTC timing book; combiners: EW, inverse-vol, Fixed-Share Hedge, risk budgeting, Hedge+RB, IC-calibrated view fusion (C3) and a decentralised consensus-ADMM combiner (`mas_trade/v2/admm.py`: neighbour-only iterations on a ring of agents, each with its own calibrated view, Hedge-weighted, against a shared risk term and the true trading cost of the net trade). Dev period only unless `--unseal`.
Dev-period findings (net of fees, impact and funding): only funding carry (Sharpe ~1.0-1.1 on all three bar sizes) and BTC timing (~0.85, mostly long-BTC beta) show a net edge; reversal has a positive rank-IC but loses money; none of the combiners beats inverse-vol; deflated Sharpe over all logged trials is not significant for any row.
