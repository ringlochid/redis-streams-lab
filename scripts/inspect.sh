#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

show() {
  local title="$1"
  shift
  echo
  echo "=== $title ==="
  "$@"
}

show "XLEN payments" docker compose exec -T redis redis-cli XLEN payments
show "XRANGE payments" docker compose exec -T redis redis-cli XRANGE payments - +
show "XINFO STREAM payments" docker compose exec -T redis redis-cli XINFO STREAM payments
show "XINFO GROUPS payments" docker compose exec -T redis redis-cli XINFO GROUPS payments
show "XPENDING payments payment-workers" docker compose exec -T redis redis-cli XPENDING payments payment-workers
show "LRANGE simulated_charges" docker compose exec -T redis redis-cli LRANGE simulated_charges 0 -1
show "LRANGE order_update_log" docker compose exec -T redis redis-cli LRANGE order_update_log 0 -1

HOT_ORDER_ID="${HOT_ORDER_ID:-}"
if [[ -n "$HOT_ORDER_ID" ]]; then
  show "HGETALL order_state:${HOT_ORDER_ID}" docker compose exec -T redis redis-cli HGETALL "order_state:${HOT_ORDER_ID}"
else
  show "KEYS order_state:*" docker compose exec -T redis redis-cli KEYS "order_state:*"
fi

echo
if [[ -f "$ROOT/data/charges.log" ]]; then
  echo "=== data/charges.log ==="
  cat "$ROOT/data/charges.log"
else
  echo "=== data/charges.log ==="
  echo "(missing)"
fi
