#!/bin/bash
# Run a command in the code of an earlier commit, for experiments whose code was deleted afterwards (replacement rule,
# decision 0032): 014 (7e68e43), 016 (ef516db), the A5 rows of 021 (93b0fe7) and the legacy experiments 001-010
# (tag legacy-v1-v2).
#
#   bash scripts/experiments/historic.sh COMMIT [--own-data] -- CMD ...
#
# The commit is checked out as a git worktree in results/historic/<commit> (gitignored; removed with
# `git worktree remove results/historic/<commit>`). Its results/ is its own, so the current saved runs and trial log are
# never touched. data/ is linked to the current data cache unless --own-data is given (the legacy code has its own
# download format, so 001-010 use --own-data).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
commit=$1; shift
own_data=
if [ "${1:-}" = "--own-data" ]; then own_data=1; shift; fi
[ "${1:-}" = "--" ] && shift
[ $# -gt 0 ] || { echo "usage: historic.sh COMMIT [--own-data] -- CMD ..."; exit 2; }

wt="results/historic/$commit"
if [ ! -d "$wt" ]; then
  mkdir -p results/historic
  git worktree add --detach "$wt" "$commit"
fi
if [ -z "$own_data" ] && [ ! -e "$wt/data" ]; then ln -s "$ROOT/data" "$wt/data"; fi
mkdir -p "$wt/results"
cd "$wt"
echo "in $(pwd) at $(git rev-parse --short HEAD): $*"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 "$@"
