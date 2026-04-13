#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/common.sh"

trap_cleanup
require_venv
lab_reset

HOT_ORDER_ID="${HOT_ORDER_ID:-order-hot-main}"
COUNT="${LAB05_COUNT:-80}"
RATE="${LAB05_RATE:-12}"
JITTER_MS="${LAB05_JITTER_MS:-80}"
UPDATE_MS="${LAB05_UPDATE_MS:-120}"
JITTER_WORKER_MS="${LAB05_WORKER_JITTER_MS:-200}"
VERBOSE="${LAB_VERBOSE:-0}"

MONITOR_LOG=/tmp/lab05_atomic_monitor.log
W1_LOG=/tmp/lab05_atomic_w1.log
W2_LOG=/tmp/lab05_atomic_w2.log
PA_LOG=/tmp/lab05_atomic_pA.log
PB_LOG=/tmp/lab05_atomic_pB.log

start_monitor "$MONITOR_LOG"

echo "[LAB05] starting atomic"
python scripts/order_worker.py --mode atomic --consumer worker-1 --batch 2 --process-ms "$UPDATE_MS" --jitter-ms "$JITTER_WORKER_MS" > "$W1_LOG" 2>&1 &
register_pid "$!"
python scripts/order_worker.py --mode atomic --consumer worker-2 --batch 2 --process-ms "$UPDATE_MS" --jitter-ms "$JITTER_WORKER_MS" > "$W2_LOG" 2>&1 &
register_pid "$!"

python scripts/producer.py "$COUNT" --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate "$RATE" --jitter-ms "$JITTER_MS" -p pA > "$PA_LOG" 2>&1 &
P1_PID=$!
python scripts/producer.py "$COUNT" --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate "$RATE" --jitter-ms "$JITTER_MS" -p pB > "$PB_LOG" 2>&1 &
P2_PID=$!

wait "$P1_PID" "$P2_PID"

sleep 1
python scripts/summary.py lab05 --hot-order-id "$HOT_ORDER_ID"

if [[ "$VERBOSE" == "1" ]]; then
  echo
  ./scripts/inspect.sh
fi

show_log_tail "Lab 05 atomic worker 1" "$W1_LOG"
show_log_tail "Lab 05 atomic worker 2" "$W2_LOG"
show_log_tail "Lab 05 atomic producer A" "$PA_LOG"
show_log_tail "Lab 05 atomic producer B" "$PB_LOG"
show_log_tail "Lab 05 atomic monitor" "$MONITOR_LOG" 12

echo

echo "Lab 05 raw logs:"
echo "  /tmp/lab05_atomic_w1.log"
echo "  /tmp/lab05_atomic_w2.log"
echo "  /tmp/lab05_atomic_pA.log"
echo "  /tmp/lab05_atomic_pB.log"
echo "  /tmp/lab05_atomic_monitor.log"

echo

echo "[LAB05] done"
