#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")/../../.."
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 uv run python run_benchmark.py --boot 500 --tag 022_three_liar_hold \
  --bar 1d --agents RankCarry TSMomentum RankReversal --consensus graph --topology complete --rounds 1 \
  --faulty RankReversal --faulty-window 2022-05-01 2022-07-31 --attack 0.01 --attack-kind noise --safety hold \
  --label "022 three graph complete, noise liar May-Jul 2022, hold (rerun after monitor fix, amendment 1)" > results/022_three_liar_hold/run.log 2>&1
echo "$(date +%T) exit=$? 022_three_liar_hold rerun" >> results/022/done.txt
