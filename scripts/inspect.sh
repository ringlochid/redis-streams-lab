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

show "XRANGE payments" docker compose exec redis redis-cli XRANGE payments - +
show "XINFO GROUPS payments" docker compose exec redis redis-cli XINFO GROUPS payments
show "XPENDING payments payment-workers" docker compose exec redis redis-cli XPENDING payments payment-workers
show "LRANGE simulated_charges" docker compose exec redis redis-cli LRANGE simulated_charges 0 -1

echo
if [[ -f "$ROOT/data/charges.log" ]]; then
  echo "=== data/charges.log ==="
  cat "$ROOT/data/charges.log"
else
  echo "=== data/charges.log ==="
  echo "(missing)"
fi
