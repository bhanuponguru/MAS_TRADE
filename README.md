# MAS_Trade

A multi-agent trading system for Binance USD-M perpetual futures, built from the AI3403 Multi-Agent Systems course material in `references/` (consensus, ADMM, distributed learning, temporal logic). Judged in absolute terms (net Sharpe against zero, P&L decomposition), never against holding BTC.

**Status: rebuild in progress** (branch `engine-rebuild`, not merged into `main`). In one line (after the volatility-limit fix, [experiment 018](docs/experiments/018-rerun-after-volatility-limit-fix.md)): the funding-carry agent works (net Sharpe 1.14 / 1.12 / 0.94 on 1d / 4h / 1h), carry + Bitcoin/Ethereum momentum reaches 1.39 / 1.48 / 1.48 but momentum narrowly fails its own admission rule and is kept as a provisional agent ([decision 0041](docs/decisions/0041-h2-kept-as-provisional-agent.md); [015](docs/experiments/015-time-series-momentum-and-the-market.md)), timing it was rejected ([016](docs/experiments/016-timing-inside-h2.md)), reversal does not pay after costs and is not admitted; with it in the roster the market beats a fixed mix by cutting its capital ([017](docs/experiments/017-reversal-and-the-market-of-three.md)). The decentralised optimiser (agents talk only to neighbours, [decision 0042](docs/decisions/0042-decentralised-cell-admm-over-a-graph.md)) gives the same result as the central hub on every network shape; sparse networks need far more communication ([019](docs/experiments/019-graph-admm-on-real-data.md), [020](docs/experiments/020-topology-and-communication-budget.md)); link failures and an offline agent leave the result unchanged, and a lying agent is detected and isolated on a robust graph ([021](docs/experiments/021-resilience.md)). The final 12 months are sealed and untouched.

## Design in one page
- **Agents = hypotheses.** Each agent runs one established quantitative hypothesis (carry, time-series momentum, short-term reversal, ...) as a full trading engine: its own forecast ("belief": expected net return per coin from a model fitted walk-forward on past data), decay estimate, risk/capacity model and execution.
- **Level 1, a wealth-staked market.** Agents stake Kelly-sized positions on their own beliefs; the system trades the netted sum. Each agent's wealth compounds with its own results, so capital moves toward the agents whose beliefs pay. Timing (when a hypothesis is likely to under- or over-perform) lives inside the belief.
- **Level 2, ADMM asset cells.** Inside the market, each (agent, coin) cell manages one coin: capacity, tail risk, cost, execution. All cells are solved jointly by ADMM; the dual variables are prices of dollar neutrality, factor exposures, margin and the net trade per coin.
- **STL** specifies and monitors: input sanity, cell loss-and-recover, execution deadlines, agent health, and the system limits that enter the ADMM as priced constraints.
- Research hygiene: point-in-time universe, no lookahead (tested), a sealed final-12-months holdout, an append-only trial log and the deflated Sharpe.

## Run
```
uv sync
uv run pytest
uv run python download_data.py [--bars 1d 4h 1h] [--top 50] [--datasets klines funding premium metrics spot]   # Binance public dumps -> data/crypto/ (gitignored)
uv run python run_benchmark.py --bar 1d   # the engine on real data, development period only
```

## History
This repository replaced an earlier implementation (a v1 consensus MAS on US stocks and crypto, and a v2 books-and-combiners engine). The experiments and decision records of that work are kept in [docs/experiments/](docs/experiments/) and [docs/decisions/](docs/decisions/); the code is at git tag `legacy-v1-v2` ([decision 0032](docs/decisions/0032-replace-v1-v2.md)).
