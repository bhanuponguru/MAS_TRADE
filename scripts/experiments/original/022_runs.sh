#!/bin/bash
# Experiment 022: seven hub runs (part A) and three graph runs (part B). Detached; progress in results/022/done.txt
cd /home/manoj/Desktop/MAS_TRADE
go() { tag=$1; shift; mkdir -p results/$tag; OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 uv run python run_benchmark.py \
  --boot 500 --tag $tag "$@" > results/$tag/run.log 2>&1; echo "$(date +%T) exit=$? $tag" >> results/022/done.txt; }
A="--agents RankCarry TSMomentum"
for bar in 1d 4h 1h; do
  go 022_${bar}_off --bar $bar $A --label "022 carry+H2 $bar safety off" &
  go 022_${bar}_derisk --bar $bar $A --safety derisk --label "022 carry+H2 $bar safety derisk" &
done
go 022_1d_hold --bar 1d $A --safety hold --label "022 carry+H2 1d safety hold" &
B="--bar 1d --agents RankCarry TSMomentum RankReversal --consensus graph --topology complete --rounds 1"
L="--faulty RankReversal --faulty-window 2022-05-01 2022-07-31 --attack 0.01 --attack-kind noise"
go 022_three_clean $B --label "022 three graph complete, no liar" &
go 022_three_liar $B $L --label "022 three graph complete, noise liar May-Jul 2022, no defence" &
go 022_three_liar_hold $B $L --safety hold --label "022 three graph complete, noise liar May-Jul 2022, hold" &
wait; echo "$(date +%T) ALL DONE" >> results/022/done.txt
