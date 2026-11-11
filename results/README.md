# Saved runs

This folder is committed on purpose, so that the results can be inspected without running anything. It is **not complete and
not current**:

| Content | Status |
|---|---|
| `_precorrection_2026-11-07/<bar>_broad_<agents>/` | the saved runs of experiments 013, 015 (unrestricted `TSMomentum` and `_restricted`), 016 (`...Timed`) and 017, made **before** the correction of the volatility limit. **Superseded by experiment 018**; the numbers in the write-ups are the corrected ones, so these runs differ from them (Sharpe ratios 0.03 to 0.2 higher, volatility drifting below 20% in later years). |
| `trials.jsonl` | the trial log of experiments 013 to 017 (42 lines, mostly repeats). It is not the complete log: it does not contain the runs of 018 to 023. The strategy trials behind the deflated Sharpe are in `docs/experiments/data/023/trial_register.csv`. |
| the corrected runs of experiments 018 to 023 | **not in the repository**; only their tables are committed under `docs/experiments/data/`. |

## Reading a run folder
- `bars.csv`: one row per bar (index is the bar's open time): `net` (system net return), `price`, `market`, `selection`, `funding`, `cost` (the return components), `btc` (Bitcoin's return) and `acc_<agent>` (each agent's account return on system equity).
- `run.log`: the printed report of the run (absolute performance, P&L components, per-agent accounts, realised skill, yearly returns); present for some runs.
- Folder names are `<bar>_broad_<agents joined by +>[_restricted]`; `_restricted` means the agent's coin set was enforced (Bitcoin and Ethereum for momentum).
- `trials.jsonl` fields: `time`, `bar`, `universe`, `name` (the variant label), `sharpe_ann`, `bars`, `unsealed`.

Runs made by `scripts/experiments/` write to `results/<tag>/` at this level, so a re-run does not touch the archived folder. See `docs/REPRODUCING.md`.
