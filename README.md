# MAS_Trade

A multi-agent trading system for Binance USD-M perpetual futures, built from the AI3403 Multi-Agent Systems course material in `references/` (consensus, ADMM, distributed learning, temporal logic). Judged in absolute terms (net Sharpe against zero, P&L decomposition), never against holding BTC.

**Status: complete on the development period** (all experiments 011 to 023 are finished; the final twelve months of data are sealed and unopened). In one line: the funding-carry agent works (net Sharpe 1.14 / 1.12 / 0.94 on daily, 4-hourly and hourly bars); the decentralised optimiser (agents talk only to neighbours) gives the same portfolio as the central one on every network shape, under link failures, with an agent offline and with a lying agent isolated; the capital market protects against a bad agent but adds nothing over a fixed mix of good agents; an STL safety monitor with a de-risking supervisor makes drawdowns shallower; and after correction for the 45 strategy variants tried, the main system's Sharpe is not conclusive on the development period alone (deflated Sharpe 0.07 to 0.10).

**The project report:** [docs/REPORT.md](docs/REPORT.md) is the formal report of the whole research, written from first principles in multi-agent-systems terms for a reader who has not seen the code; it is the basis of the final project presentation.

## Design in one page
- **Agents = hypotheses.** Each agent runs one established quantitative hypothesis (carry, time-series momentum, short-term reversal, ...) as a full trading engine: its own forecast ("belief": expected net return per coin from a model fitted walk-forward on past data), decay estimate, risk/capacity model and execution.
- **Level 1, a wealth-staked market.** Agents stake Kelly-sized positions on their own beliefs; the system trades the netted sum. Each agent's wealth compounds with its own results, so capital moves toward the agents whose beliefs pay. Timing (when a hypothesis is likely to under- or over-perform) lives inside the belief.
- **Level 2, ADMM asset cells.** Inside the market, each (agent, coin) cell manages one coin: capacity, tail risk, cost, execution. All cells are solved jointly by ADMM; the dual variables are prices of dollar neutrality, factor exposures, margin and the net trade per coin.
- **STL** specifies and monitors: input sanity, cell loss-and-recover, execution deadlines, agent health, and the system limits that enter the ADMM as priced constraints.
- Research hygiene: point-in-time universe, no lookahead (tested), a sealed final-12-months holdout, an append-only trial log and the deflated Sharpe.

## Run
```
uv sync
uv run pytest                                              # all tests (about 7 minutes)
uv run python download_data.py [--bars 1d 4h 1h] [--top 50] [--datasets klines funding premium metrics spot]   # Binance public dumps -> data/crypto/ (gitignored)
uv run python run_benchmark.py --bar 1d --agents RankCarry TSMomentum    # the engine on real data, development period only
uv run --group dashboard streamlit run dashboard.py        # the interactive dashboard
```
The sealed window is the 12 months before the last downloaded bar, so results depend on the data snapshot (the published numbers use one ending on 2026-11-05). Every experiment has a script in `scripts/experiments/` (for example `bash scripts/experiments/022_safety.sh`). How every result was produced, what is and is not in the repository, and the known gaps are in [docs/REPRODUCING.md](docs/REPRODUCING.md).

## Documentation
- [docs/REPORT.md](docs/REPORT.md) the research report; [docs/REPRODUCING.md](docs/REPRODUCING.md) reproduction notes.
- [docs/experiments/](docs/experiments/) one write-up per experiment with its exact command and result tables; [docs/decisions/](docs/decisions/) one record per design decision.

## History
This repository replaced an earlier implementation (a v1 consensus MAS on US stocks and crypto, and a v2 books-and-combiners engine). The experiments and decision records of that work are kept in [docs/experiments/](docs/experiments/) and [docs/decisions/](docs/decisions/); the code is at git tag `legacy-v1-v2` (commit `cf16351`) ([decision 0032](docs/decisions/0032-replace-v1-v2.md)).
