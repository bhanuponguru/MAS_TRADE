#!/bin/bash
cd /home/manoj/Desktop/MAS_TRADE
go() { tag=$1; shift; mkdir -p results/$tag; OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 uv run python run_benchmark.py --bar 1d \
  --agents RankCarry TSMomentum RankReversal --boot 500 --tag $tag "$@" > results/$tag/run.log 2>&1; echo "$(date +%T) exit=$? $tag" >> results/step1_done.txt; }
go 1d_broad_three_graph_complete --consensus graph --topology complete --label "019 market of three, graph complete" &
go 1d_broad_three_graph_line --consensus graph --topology line --label "019 market of three, graph line" &
go 1d_broad_three_graph_line_r3 --consensus graph --topology line --rounds 3 --label "019 market of three, graph line, 3 rounds" &
wait; echo "$(date +%T) ALL DONE" >> results/step1_done.txt
