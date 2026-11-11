#!/bin/bash
# Experiment 017, H4 residual reversal alone and the market of three, then the pre-registered gates (compare_reversal.py).
# Needs the runs of 013 and 015 (run here if missing). Runs as re-made in experiment 018 (volatility-limit fix).
source "$(dirname "$0")/common.sh"
runs_013; runs_015; runs_017; wait
uv run python compare_reversal.py                      # docs/experiments/data/017/comparison.csv
