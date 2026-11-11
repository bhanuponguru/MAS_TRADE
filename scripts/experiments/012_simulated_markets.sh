#!/bin/bash
# Experiment 012, both MAS levels on simulated data: the tests are the experiment (no real data needed).
source "$(dirname "$0")/common.sh"
uv run pytest tests/test_cells_admm.py tests/test_market.py tests/test_averaging.py tests/test_stl.py tests/test_timing.py "$@"
