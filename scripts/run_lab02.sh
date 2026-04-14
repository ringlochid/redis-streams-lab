#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/common.sh"

trap_cleanup
require_venv
lab_reset

COUNT="${LAB02_COUNT:-3}"
PRODUCER_ID="${LAB02_PRODUCER_ID:-failer}"
VERBOSE="${LAB_VERBOSE:-0}"

MONITOR_LOG=/tmp/lab02_monitor.log
WORKER_LOG=/tmp/lab02_worker.log
PRODUCER_LOG=/tmp/lab02_producer.log

start_monitor "$MONITOR_LOG"

echo "[LAB02] starting"
python scripts/worker.py --consumer worker-1 --crash-after-side-effect > "$WORKER_LOG" 2>&1 &
register_pid "$!"

python scripts/producer.py "$COUNT" --producer-id "$PRODUCER_ID" > "$PRODUCER_LOG" 2>&1
sleep 1

python scripts/summary.py lab02
echo
python scripts/evidence.py lab02 --monitor-log "$MONITOR_LOG"

if [[ "$VERBOSE" == "1" ]]; then
  echo
  ./scripts/inspect.sh
fi

show_log_tail "Lab 02 worker (crash mode)" "$WORKER_LOG"
show_log_tail "Lab 02 producer" "$PRODUCER_LOG"
show_log_tail "Lab 02 monitor" "$MONITOR_LOG" 12

echo

echo "Lab 02 raw logs:"
echo "  /tmp/lab02_worker.log"
echo "  /tmp/lab02_producer.log"
echo "  /tmp/lab02_monitor.log"

echo

echo "[LAB02] done"
