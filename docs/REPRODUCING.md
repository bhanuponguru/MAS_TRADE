# Reproducing the results

No full re-run is planned. This note records how every result was produced, so that a re-run is possible, and lists the known caveats. Nothing here has been re-executed since the experiments were written up.

## What is in the repository and what is not

| In the repository | Not in the repository (gitignored or on another machine) |
|---|---|
| All code, the tests, the pre-registered rules and the write-up of every experiment (`docs/experiments/`), the decisions (`docs/decisions/`), and the small result tables of every experiment (`docs/experiments/data/`) | the raw data (`data/`, about 1.9 GB), the saved runs (`results/`), the trial log (`results/trials.jsonl`) |
| The legacy implementation, at git tag `legacy-v1-v2` (commit `cf16351`) | the saved runs of experiments 018 to 023, which were produced on the second contributor's machine |
| A register of the strategy variants behind the deflated Sharpe: `docs/experiments/data/023/trial_register.csv` | the original batch scripts of experiment 022 (`results/022/runs.sh`, `rerun_hold.sh`) |

Every number in the report can therefore be traced to a committed table, but the saved runs behind the tables of experiments 018 to 023 cannot be regenerated without re-running them.

## Environment

`uv sync` (Python 3.12 or newer; versions are pinned by `uv.lock`). The dashboard needs `uv sync --group dashboard`. The solver is deterministic for fixed data and settings; the runs were made with single-threaded BLAS (`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`, which `run_topology.py` and `run_resilience.py` set themselves and the tests pin). Exact iteration counts at the solver's iteration cap could differ on another platform.

## The data snapshot (read this before re-running)

- Source: Binance's public data archive, downloaded with `download_data.py` (klines for 1d, 4h and 1h, funding, premium index, spot, and optionally open-interest metrics). Open-interest data are only needed for the carry-ladder rungs that were not run.
- The snapshot used for the results ends on **2026-11-05** (the last Bitcoin daily bar). The development period is April 2020 to November 2025: trading starts on 2020-04-30 and the development period ends on 2025-11-04 (daily bars) and 2025-11-05 (4-hourly and hourly bars).
- **The sealed window is defined relative to the last downloaded bar** (the 12 months before it). A download made on a later date moves the split and changes every number. To reproduce the results, truncate or pin the data to the snapshot above before running; the code does not do this by itself.
- The sealed final year has not been examined and must only be opened once, with `--unseal`, after the design is frozen.

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
| 022 safety | `run_benchmark.py ... --safety off|derisk|hold` and the liar options (`--faulty`, `--attack`, `--attack-kind noise`, `--faulty-window`); ten runs, tags `022_*`. The original batch script is not in the repository | hours (an undefended liar run does not finish: its solves diverge) |
| 023 final table | `final_table.py` (reads the saved runs of 018 to 022 and the trial log) | seconds, after the runs exist |
| Dashboard | `uv run --group dashboard streamlit run dashboard.py` | interactive |

Experiments 014 (funding forecast) and 016 (timing) used code that was deleted when the experiments were rejected; it is kept in the history (`8360532` and `394314e` respectively), and the trimmed-mixing variant of experiment 021 at `4194d43`. The legacy experiments 001 to 010 are reproduced by checking out the tag `legacy-v1-v2`.

## The trial log and the deflated Sharpe

Every run appends a line to `results/trials.jsonl`; the file is not committed, because it is specific to the machine that made the runs (the one on the first contributor's machine has 42 lines, mostly repeats). The strategy trials counted in the deflated Sharpe of experiment 023 are listed in `docs/experiments/data/023/trial_register.csv`.

The written enumeration of experiment 023 sums to **16** strategy variants (48 trials over three bar sizes), while the text states 15 (45 trials). The register follows the enumeration. The difference is small and in the conservative direction: at 48 trials the deflated Sharpe of the daily main system falls from 0.070 to about 0.063 (computed from the same inputs, with the number of periods approximated), so the verdict is unchanged.

## Known gaps

- The saved runs of experiments 018 to 023 are on another machine; only their tables are committed.
- The data snapshot is not archived, and the sealed split moves with the last downloaded bar (see above).
- The course lecture PDFs cited in the README (`references/`) are not in the repository.
