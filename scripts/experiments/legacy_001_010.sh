#!/bin/bash
# The legacy experiments 001-010 (stock and v1/v2 crypto systems), in the code at tag legacy-v1-v2, with that code's own
# data download. Output inside results/historic/legacy-v1-v2.
#   bash scripts/experiments/legacy_001_010.sh 001|002|003|004|005|006|007|008|009|010 [BAR]     BAR for 005-007 (default 1d)
# 010: only the `uniform` variant can be re-run (--exp all); the `risk` allocation was never committed (its code is in the
# appendix of docs/experiments/010-shield-allocation-across-agents.md) and --exp d029 no longer exists.
set -euo pipefail
cd "$(dirname "$0")/../.."
H="bash scripts/experiments/historic.sh legacy-v1-v2 --own-data --"
bar=${2:-1d}
case "${1:-}" in
  001|004|008) $H uv run python run_backtest.py ;;
  002) $H uv run python run_backtest.py --mode wmsr; $H uv run python run_backtest.py --mode admm ;;
  003) $H uv run python run_adversary_experiment.py; $H uv run python run_adversary_experiment.py --hier ;;
  005) [ -d results/historic/legacy-v1-v2/data/crypto ] || $H uv run python download_crypto_data.py
       $H uv run python run_crypto_benchmark.py --bar "$bar" ;;
  006|007) [ -d results/historic/legacy-v1-v2/data/crypto ] || $H uv run python download_crypto_data.py
       $H uv run python run_v2_benchmark.py --bar "$bar" --universe broad ;;
  009) $H uv run python run_safety_experiments.py --exp d028 ;;
  010) $H uv run python run_safety_experiments.py --exp all
       echo "note: this gives the uniform variant only; the risk variant of 010 needs the code in the write-up appendix" ;;
  *) echo "usage: legacy_001_010.sh 001..010 [BAR]"; exit 2 ;;
esac
