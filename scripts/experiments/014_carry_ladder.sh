#!/bin/bash
# Experiment 014, carry ladder rung R1: the mechanical gate of the funding forecast (failed; no P&L run).
# The code was deleted after the experiment; this runs it at commit 8360532. Output: the gate table printed, and
# docs/experiments/data/014/gate.csv inside results/historic/8360532 (compare with the committed one).
exec bash "$(dirname "$0")/historic.sh" 8360532 -- uv run python run_funding_gate.py
