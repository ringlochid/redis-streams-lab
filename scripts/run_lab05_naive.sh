#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .venv/bin/activate ]]; then
  echo "Missing .venv. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi
source .venv/bin/activate

HOT_ORDER_ID="${HOT_ORDER_ID:-order-hot-main}"
COUNT="${LAB05_COUNT:-80}"
RATE="${LAB05_RATE:-12}"
JITTER_MS="${LAB05_JITTER_MS:-80}"
UPDATE_MS="${LAB05_UPDATE_MS:-120}"
JITTER_WORKER_MS="${LAB05_WORKER_JITTER_MS:-200}"

cleanup() {
  for pid in "${WORKER_1_PID:-}" "${WORKER_2_PID:-}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

./scripts/reset.sh >/dev/null

export HOT_ORDER_ID

: > /tmp/lab05_naive_w1.log
: > /tmp/lab05_naive_w2.log
: > /tmp/lab05_naive_pA.log
: > /tmp/lab05_naive_pB.log

echo "[LAB05] starting naive workers and hot stream (order=${HOT_ORDER_ID})"
python scripts/order_worker.py --mode naive --consumer worker-1 --batch 2 --process-ms "$UPDATE_MS" --jitter-ms "$JITTER_WORKER_MS" > /tmp/lab05_naive_w1.log 2>&1 &
WORKER_1_PID=$!
python scripts/order_worker.py --mode naive --consumer worker-2 --batch 2 --process-ms "$UPDATE_MS" --jitter-ms "$JITTER_WORKER_MS" > /tmp/lab05_naive_w2.log 2>&1 &
WORKER_2_PID=$!

python scripts/producer.py "$COUNT" --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate "$RATE" --jitter-ms "$JITTER_MS" -p pA > /tmp/lab05_naive_pA.log 2>&1 &
PRODUCER_1_PID=$!
python scripts/producer.py "$COUNT" --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate "$RATE" --jitter-ms "$JITTER_MS" -p pB > /tmp/lab05_naive_pB.log 2>&1 &
PRODUCER_2_PID=$!

wait "$PRODUCER_1_PID" "$PRODUCER_2_PID"

sleep 1
HOT_ORDER_ID="$HOT_ORDER_ID" ./scripts/inspect.sh

echo
EXPECTED_DELTA=$(python - <<'PY'
from scripts.common import redis_client, STREAM
r = redis_client()
entries = r.xrange(STREAM, "-", "+")
sum_delta = 0
for _, fields in entries:
    if fields.get("event") == "order_delta":
        sum_delta += int(fields.get("delta", "0"))
print(sum_delta)
PY
)

echo "[LAB05] expected total delta: $EXPECTED_DELTA"
