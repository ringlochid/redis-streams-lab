#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/common.sh"

trap_cleanup
require_venv
lab_reset

COUNT="${LAB01_COUNT:-20}"
RATE="${LAB01_RATE:-2}"
PRODUCER_ID="${LAB01_PRODUCER_ID:-p1}"
PROCESS_MS="${LAB01_PROCESS_MS:-0}"
VERBOSE="${LAB_VERBOSE:-0}"

MONITOR_LOG=/tmp/lab01_monitor.log
WORKER_LOG=/tmp/lab01_worker.log
PRODUCER_LOG=/tmp/lab01_producer.log

start_monitor "$MONITOR_LOG"

echo "[LAB01] starting"
python scripts/worker.py --consumer worker-1 --process-ms "$PROCESS_MS" > "$WORKER_LOG" 2>&1 &
register_pid "$!"

python scripts/producer.py "$COUNT" --producer-id "$PRODUCER_ID" --rate "$RATE" > "$PRODUCER_LOG" 2>&1
sleep 1

python scripts/summary.py lab01

if [[ "$VERBOSE" == "1" ]]; then
  echo
  ./scripts/inspect.sh
fi

show_log_tail "Lab 01 worker" "$WORKER_LOG"
show_log_tail "Lab 01 producer" "$PRODUCER_LOG"
show_log_tail "Lab 01 monitor" "$MONITOR_LOG" 12

if [[ -n "$MONITOR_LOG" ]]; then
  echo
  echo "Lab 01 raw logs:"
  echo "  /tmp/lab01_worker.log"
  echo "  /tmp/lab01_producer.log"
  echo "  /tmp/lab01_monitor.log"
fi

echo

echo "[LAB01] done"
