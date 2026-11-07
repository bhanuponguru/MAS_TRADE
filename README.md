# MAS_Trade

A multi-agent trading system for Binance USD-M perpetual futures, built from the AI3403 Multi-Agent Systems course material in `references/` (consensus, ADMM, distributed learning, temporal logic). Judged in absolute terms (net Sharpe against zero, P&L decomposition), never against holding BTC.

**Status: rebuild in progress** (branch `engine-rebuild`). Built and validated: the data pipeline (extended Binance dataset), the cost model, the joint ADMM over (agent, coin) cells, the wealth-staked market and model averaging, STL specs and timing (checked on simulated data, [experiment 012](docs/experiments/012-mas-levels-on-simulated-data.md)), and the real-data engine with the carry agent (net Sharpe 1.27 / 1.12 / 1.00 on 1d / 4h / 1h in the development period, [experiment 013](docs/experiments/013-carry-baseline-on-real-data.md)). Next: the carry ladder and the other hypothesis agents. The final 12 months are sealed and untouched.

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
