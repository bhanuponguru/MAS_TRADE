# Shared helpers of the experiment scripts (sourced, not run). Every script runs from the repository root, dev period only.
#
#   bench TAG ARGS...   one run_benchmark.py run (--boot 500, as in every write-up) into results/TAG/run.log.
#                       Skipped when results/TAG/run.log already ends a finished run; FORCE=1 re-runs it.
#   spawn CMD...        run CMD in the background, at most $JOBS (default 4) at a time; finish with `wait`.
#
# Each run appends a line to results/trials.jsonl (the trial log of the deflated Sharpe). Re-running a variant adds a
# repeat line, not a new trial: final_table.py drops repeats by (bar, name). Labels are kept exactly as in the original
# runs, because final_table.py selects trials by label.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1   # single-threaded BLAS, as in every run
JOBS=${JOBS:-4}
BARS=${BARS:-"1d 4h 1h"}

bench() {
  local tag=$1; shift
  if [ -z "${FORCE:-}" ] && grep -q "^written to" "results/$tag/run.log" 2>/dev/null; then
    echo "skip (finished): $tag"; return 0
  fi
  mkdir -p "results/$tag"
  echo "$(date +%T) start  $tag"
  if nice -n 10 uv run python run_benchmark.py --boot 500 --tag "$tag" "$@" > "results/$tag/run.log" 2>&1; then
    echo "$(date +%T) done   $tag"
  else
    echo "$(date +%T) FAILED $tag (see results/$tag/run.log)"
  fi
}

spawn() {
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n || true; done
  "$@" &
}

# The real-data runs of experiments 013, 015b and 017, as re-run after the volatility-limit fix (experiment 018).
# These are the runs every later comparison reads.
runs_013() { for b in $BARS; do spawn bench "${b}_broad_RankCarry" --bar "$b" --agents RankCarry --label "013 carry (vol fix)"; done; }
runs_015() {
  for b in $BARS; do
    spawn bench "${b}_broad_TSMomentum_restricted" --bar "$b" --agents TSMomentum --label "015b H2 alone (vol fix)"
    spawn bench "${b}_broad_RankCarry+TSMomentum_restricted" --bar "$b" --agents RankCarry TSMomentum --label "015b market of two (vol fix)"
  done
}
runs_017() {
  for b in $BARS; do
    spawn bench "${b}_broad_RankReversal" --bar "$b" --agents RankReversal --label "017 reversal alone (vol fix)"
    spawn bench "${b}_broad_RankCarry+TSMomentum+RankReversal" --bar "$b" --agents RankCarry TSMomentum RankReversal --label "017 market of three (vol fix)"
  done
}

# The eight-agent roster of experiments 020 and 021 (agent:holding period in bars).
EIGHT="RankCarry:7 RankCarry:14 RankCarry:30 TSMomentum:15 TSMomentum:30 TSMomentum:60 RankReversal:3 RankReversal:7"
