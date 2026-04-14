#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/common.sh"

trap_cleanup
require_venv
lab_reset

COUNT="${LAB03_COUNT:-3}"
PRODUCER_ID="${LAB03_PRODUCER_ID:-recover}"
VERBOSE="${LAB_VERBOSE:-0}"

MONITOR_LOG=/tmp/lab03_monitor.log
WORKER1_LOG=/tmp/lab03_worker1.log
WORKER2_LOG=/tmp/lab03_worker2.log
PRODUCER_LOG=/tmp/lab03_producer.log
CLAIM_LOG=/tmp/lab03_claim.log

start_monitor "$MONITOR_LOG"

echo "[LAB03] starting"
python scripts/worker.py --consumer worker-1 --crash-after-side-effect > "$WORKER1_LOG" 2>&1 &
register_pid "$!"

python scripts/producer.py "$COUNT" --producer-id "$PRODUCER_ID" > "$PRODUCER_LOG" 2>&1
sleep 1

docker compose exec -T redis redis-cli XAUTOCLAIM payments payment-workers worker-2 0 0-0 COUNT 10 > "$CLAIM_LOG" 2>&1

python scripts/worker.py --consumer worker-2 > "$WORKER2_LOG" 2>&1 &
register_pid "$!"
sleep 2

python scripts/summary.py lab03
echo
python scripts/evidence.py lab03 --monitor-log "$MONITOR_LOG"

if [[ "$VERBOSE" == "1" ]]; then
  echo
  ./scripts/inspect.sh
fi

show_log_tail "Lab 03 worker 1 (crashed)" "$WORKER1_LOG"
show_log_tail "Lab 03 claim output" "$CLAIM_LOG"
show_log_tail "Lab 03 worker 2 (recovered)" "$WORKER2_LOG"
show_log_tail "Lab 03 producer" "$PRODUCER_LOG"
show_log_tail "Lab 03 monitor" "$MONITOR_LOG" 12

echo

echo "Lab 03 raw logs:"
echo "  /tmp/lab03_worker1.log"
echo "  /tmp/lab03_worker2.log"
echo "  /tmp/lab03_producer.log"
echo "  /tmp/lab03_claim.log"
echo "  /tmp/lab03_monitor.log"

echo

echo "[LAB03] done"
