# Reproducing the results

No full re-run is planned. This note records how every result was produced, so that a re-run is possible, and lists the known caveats. Nothing here has been re-executed since the experiments were written up.

## What is in the repository and what is not

| In the repository | Not in the repository (gitignored or on another machine) |
|---|---|
| All code, the tests, the pre-registered rules and the write-up of every experiment (`docs/experiments/`), the decisions (`docs/decisions/`), and the small result tables of every experiment (`docs/experiments/data/`) | the raw data (`data/`, about 1.9 GB), the saved runs (`results/`), the trial log (`results/trials.jsonl`) |
| The legacy implementation, at git tag `legacy-v1-v2` (commit `b24f70a`) | the saved runs of experiments 018 to 023, which were produced on the second contributor's machine |
| A register of the strategy variants behind the deflated Sharpe: `docs/experiments/data/023/trial_register.csv` | |
| One script per experiment (`scripts/experiments/`), the original batch scripts of 018 to 022 (`scripts/experiments/original/`) and the code of the tables of 020, 021 and 022 (`experiment_tables.py`) | |

Every number in the report can therefore be traced to a committed table, but the saved runs behind the tables of experiments 018 to 023 cannot be regenerated without re-running them. The scripts below re-run them.

## Environment

`uv sync` (Python 3.12 or newer; versions are pinned by `uv.lock`). The dashboard needs `uv sync --group dashboard`. The solver is deterministic for fixed data and settings; the runs were made with single-threaded BLAS (`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`, which `run_topology.py` and `run_resilience.py` set themselves and the tests pin). Exact iteration counts at the solver's iteration cap could differ on another platform.

## The data snapshot (read this before re-running)

- Source: Binance's public data archive, downloaded with `download_data.py` (klines for 1d, 4h and 1h, funding, premium index, spot, and optionally open-interest metrics). Open-interest data are only needed for the carry-ladder rungs that were not run.
- The snapshot used for the results ends on **2026-11-05** (the last Bitcoin daily bar). The development period is April 2020 to November 2025: trading starts on 2020-04-30 and the development period ends on 2025-11-04 (daily bars) and 2025-11-05 (4-hourly and hourly bars).
- **The sealed window is defined relative to the last downloaded bar** (the 12 months before it). A download made on a later date moves the split and changes every number. To reproduce the results, truncate or pin the data to the snapshot above before running; the code does not do this by itself.
- The sealed final year has not been examined and must only be opened once, with `--unseal`, after the design is frozen.

## One script per experiment

`scripts/experiments/` has a script for every experiment; run them from anywhere (they move to the repository root). Each engine run goes to `results/<tag>/run.log` with the tag and trial-log label of the original run, single-threaded BLAS and `--boot 500`; a run whose log shows it finished is skipped (`FORCE=1` re-runs it), up to `JOBS` runs (default 4) go in parallel, and `BARS="1d"` limits the bar sizes. With the saved runs present, the scripts regenerate the committed tables of 015, 017, 018, 020, 021, 022 and 023 byte for byte (checked on 2026-11-11).

| Script | Experiment |
|---|---|
| `000_download_data.sh [--with-metrics]` | the data cache (read the snapshot note above first) |
| `011_data_audit.sh`, `012_simulated_markets.sh` | data audit; simulated markets (the tests) |
| `013_carry.sh`, `015_momentum.sh`, `017_reversal.sh` | the real-data runs of 013, 015b and 017 as re-run in 018, and their comparisons |
| `018_rerun_all.sh` | all fifteen runs of 018 and every table read from them |
| `019_graph_admm.sh`, `020_topology.sh [partA\|partB\|tables]`, `021_resilience.sh [partA\|partA5\|partB\|tables]`, `022_safety.sh [runs\|tables]` | 019 to 022; the tables of 020, 021 and 022 come from `experiment_tables.py` |
| `023_final_table.sh` | the final comparison (after 018 to 022) |
| `run_all.sh` | 012 and 018 to 023 in order (many hours) |
| `014_carry_ladder.sh`, `016_timing.sh`, `021_resilience.sh partA5`, `legacy_001_010.sh 001..010` | experiments whose code was deleted: run at their commit by `historic.sh` in a git worktree under `results/historic/<commit>`, with their own `results/` so the current runs and trial log are not touched |

The undefended liar runs (`021_liar_none`, `022_three_liar`) never finish (their solves diverge), so the scripts start them only with `WITH_UNDEFENDED_LIAR=1`. The first H2 runs of 015 (before H2 was restricted to Bitcoin and Ethereum) and the pre-fix runs of 013, 015 and 017 are superseded by 018 and are not re-made; 016 is re-made with its own (pre-fix) engine, as originally. Experiment 010 can only be re-run for the `uniform` variant.

## Experiments, commands and cost

Commands are as given in each experiment write-up; all runs are on the development period. "B" is a bar size (1d, 4h, 1h). Times are approximate, for one run on a laptop with single-threaded BLAS.

| Experiment | What produces it | Time |
|---|---|---|
| 011 data audit | `download_data.py ... --coverage` (see the write-up) | minutes |
| 012 simulated markets | `uv run pytest` (the tests are the experiment) | 7 minutes for the whole suite |
| 013, 018 carry, momentum, reversal and the markets | `run_benchmark.py --bar B --agents <agents> --label "<name>" --tag B_broad_<tag> --boot 500`; agents and tags are listed in the 018 write-up | 1d about 1 minute; 4h 5 to 45 minutes; 1h 5 to 60 minutes (the three-agent hourly run about an hour) |
| 015, 017 comparisons | `compare_runs.py --suffix _restricted`, `compare_blend.py`, `compare_reversal.py` (read saved runs) | seconds |
| 019 decentralised against hub | `run_benchmark.py --bar 1d --agents RankCarry TSMomentum RankReversal --consensus graph --topology complete|line [--rounds 3]` | minutes |
| 020 topology | `run_topology.py --workers 4` (Part A); Part B commands in the write-up | about 3 hours |
| 021 resilience | `run_resilience.py --workers 3` (Part A); Part B commands in the write-up | about 3.5 hours |
| 022 safety | `run_benchmark.py ... --safety off|derisk|hold` and the liar options (`--faulty`, `--attack`, `--attack-kind noise`, `--faulty-window`); ten runs, tags `022_*` (`scripts/experiments/022_safety.sh`; original batch scripts in `scripts/experiments/original/`); tables by `experiment_tables.py 022` | hours (an undefended liar run does not finish: its solves diverge) |
| 023 final table | `final_table.py` (reads the saved runs of 018 to 022 and the trial log) | seconds, after the runs exist |
| Dashboard | `uv run --group dashboard streamlit run dashboard.py` | interactive |

Experiments 014 (funding forecast) and 016 (timing) used code that was deleted when the experiments were rejected; it is kept in the history (`7e68e43` and `ef516db` respectively), and the trimmed-mixing variant of experiment 021 at `93b0fe7`. The legacy experiments 001 to 010 are reproduced by checking out the tag `legacy-v1-v2`.

## The trial log and the deflated Sharpe

Every run appends a line to `results/trials.jsonl`; the file is not committed, because it is specific to the machine that made the runs (the one on the first contributor's machine has 42 lines, mostly repeats). The strategy trials counted in the deflated Sharpe of experiment 023 are listed in `docs/experiments/data/023/trial_register.csv`.

The written enumeration of experiment 023 sums to **16** strategy variants (48 trials over three bar sizes), while the text states 15 (45 trials). The register follows the enumeration. The difference is small and in the conservative direction: at 48 trials the deflated Sharpe of the daily main system falls from 0.070 to about 0.063 (computed from the same inputs, with the number of periods approximated), so the verdict is unchanged.

## Known gaps

- The saved runs of experiments 018 to 023 are on another machine; only their tables are committed.
- The data snapshot is not archived, and the sealed split moves with the last downloaded bar (see above).
- The course lecture PDFs cited in the README (`references/`) are not in the repository.
