#!/bin/bash
# Step 0 re-runs (experiment 018): runs only the jobs without a finished run.log, detached from any terminal.
# Usage: bash scripts/experiments/original/018_step0_resume.sh      Progress: cat results/step0_done.txt
SELF="$(readlink -f "$0")"
HERE="$(dirname "$SELF")"
cd "$HERE/../../.."
run() {
  IFS='|' read -r bar agents tag label <<< "$1"
  grep -q "^written to" "results/$tag/run.log" 2>/dev/null && return
  mkdir -p "results/$tag"
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 10 uv run python run_benchmark.py --bar $bar --agents $agents \
    --label "$label" --tag "$tag" --boot 500 > "results/$tag/run.log" 2>&1
  echo "$(date +%T) exit=$? $tag" >> results/step0_done.txt
}
export -f run
if [ "$1" != "--inner" ]; then nohup setsid bash "$SELF" --inner > /dev/null 2>&1 < /dev/null & echo "started detached"; exit; fi
tr '\n' '\0' < "$HERE/018_step0_jobs.txt" | xargs -0 -P 4 -I{} bash -c 'run "$@"' _ {}
echo "$(date +%T) ALL DONE" >> results/step0_done.txt
