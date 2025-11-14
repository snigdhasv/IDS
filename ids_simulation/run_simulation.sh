#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/.."
MODE="${MODE:-cicids}"
RATE="${RATE:-50}"
ACTION="${1:-start}"
PY="$DIR/simulate_ids_pipeline.py"
if [ "$ACTION" = "start" ]; then
  nohup python3 "$PY" start --mode "$MODE" --rate "$RATE" >/dev/null 2>&1 &
  echo "simulation started"
elif [ "$ACTION" = "stop" ]; then
  python3 "$PY" stop || true
elif [ "$ACTION" = "status" ]; then
  python3 "$PY" status
else
  echo "usage: run_simulation.sh [start|stop|status]" && exit 1
fi