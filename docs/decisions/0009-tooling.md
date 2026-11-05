# 0009. Tooling: uv, data and results out of git

Status: **Accepted**   Date: 2026-10-20   Commit: `8e1b394`   Where: `pyproject.toml`, `.gitignore`

## Decision
- `uv` for environments and running (`uv sync`, `uv run ...`), no pip/venv.
- `data/` and `results/` are gitignored: data is re-downloadable and results are re-computable.
- Every tunable lives in the `Config` dataclass; variants use `dataclasses.replace`.

## Consequence
Results are not versioned, so numbers that matter must be written into `docs/experiments/` (this log).
