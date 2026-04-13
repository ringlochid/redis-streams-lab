#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/common.sh"

trap_cleanup
require_venv
lab_reset

COUNT="${LAB04_COUNT:-60}"
RATE="${LAB04_RATE:-6}"
PRODUCER_JITTER_MS="${LAB04_PRODUCER_JITTER_MS:-80}"
WORKER_PROCESS_MS="${LAB04_WORKER_PROCESS_MS:-200}"
WORKER_JITTER_MS="${LAB04_WORKER_JITTER_MS:-80}"
VERBOSE="${LAB_VERBOSE:-0}"

MONITOR_LOG=/tmp/lab04_monitor.log
W1_LOG=/tmp/lab04_w1.log
W2_LOG=/tmp/lab04_w2.log
W3_LOG=/tmp/lab04_w3.log
P1_LOG=/tmp/lab04_p1.log
P2_LOG=/tmp/lab04_p2.log

start_monitor "$MONITOR_LOG"

echo "[LAB04] starting"
python scripts/worker.py --consumer worker-1 --batch 2 --process-ms "$WORKER_PROCESS_MS" --jitter-ms "$WORKER_JITTER_MS" > "$W1_LOG" 2>&1 &
register_pid "$!"
python scripts/worker.py --consumer worker-2 --batch 2 --process-ms "$WORKER_PROCESS_MS" --jitter-ms "$WORKER_JITTER_MS" > "$W2_LOG" 2>&1 &
register_pid "$!"
python scripts/worker.py --consumer worker-3 --batch 2 --process-ms "$WORKER_PROCESS_MS" --jitter-ms "$WORKER_JITTER_MS" > "$W3_LOG" 2>&1 &
register_pid "$!"

python scripts/producer.py "$COUNT" --producer-id p1 --rate "$RATE" --jitter-ms "$PRODUCER_JITTER_MS" > "$P1_LOG" 2>&1 &
P1_PID=$!
python scripts/producer.py "$COUNT" order-B --producer-id p2 --rate "$RATE" --jitter-ms "$PRODUCER_JITTER_MS" > "$P2_LOG" 2>&1 &
P2_PID=$!

wait "$P1_PID" "$P2_PID"
sleep 2

python scripts/summary.py lab04

if [[ "$VERBOSE" == "1" ]]; then
  echo
  ./scripts/inspect.sh
fi

show_log_tail "Lab 04 worker 1" "$W1_LOG"
show_log_tail "Lab 04 worker 2" "$W2_LOG"
show_log_tail "Lab 04 worker 3" "$W3_LOG"
show_log_tail "Lab 04 producer 1" "$P1_LOG"
show_log_tail "Lab 04 producer 2" "$P2_LOG"
show_log_tail "Lab 04 monitor" "$MONITOR_LOG" 12

echo

echo "Lab 04 raw logs:"
echo "  /tmp/lab04_w1.log"
echo "  /tmp/lab04_w2.log"
echo "  /tmp/lab04_w3.log"
echo "  /tmp/lab04_p1.log"
echo "  /tmp/lab04_p2.log"
echo "  /tmp/lab04_monitor.log"

echo

echo "[LAB04] done"
