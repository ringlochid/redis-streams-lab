#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose up -d >/dev/null
docker compose exec redis redis-cli FLUSHDB >/dev/null
rm -f "$ROOT/data/charges.log"

echo "reset complete"
