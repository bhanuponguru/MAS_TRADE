#!/bin/bash
# Experiment 015 (015b, Amendment 1): H2 time-series momentum alone and the market of carry and H2, then the
# pre-registered comparisons and the fixed-weight blend control. Needs the carry runs of 013 (run here if missing).
# The runs are those of experiment 018 (volatility-limit fix). The first, unrestricted H2 runs of 015 are superseded
# (H2 is now BTC/ETH only) and cannot be made with the current code.
source "$(dirname "$0")/common.sh"
runs_013; runs_015; wait
uv run python compare_runs.py --suffix _restricted     # docs/experiments/data/015/comparison_restricted.csv
uv run python compare_blend.py                         # docs/experiments/data/015/blend_control.csv
