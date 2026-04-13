#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLEANUP_PIDS=()

register_pid() {
  CLEANUP_PIDS+=("$1")
}

cleanup_all() {
  for (( idx=${#CLEANUP_PIDS[@]}-1; idx>=0; idx-- )); do
    local pid="${CLEANUP_PIDS[$idx]}"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}

trap_cleanup() {
  trap cleanup_all EXIT
}

require_venv() {
  cd "$ROOT"
  if [[ ! -f .venv/bin/activate ]]; then
    echo "Missing .venv. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
}

ensure_redis() {
  cd "$ROOT"
  docker compose up -d redis >/dev/null
}

lab_reset() {
  cd "$ROOT"
  ./scripts/reset.sh >/dev/null
}

start_monitor() {
  local log="$1"
  cd "$ROOT"
  ensure_redis
  : > "$log"
  docker exec redis-streams-lab redis-cli MONITOR > "$log" 2>&1 &
  register_pid "$!"
  sleep 1
}

show_section() {
  echo
  echo "=== $1 ==="
}

show_log_tail() {
  local label="$1"
  local path="$2"
  local lines="${3:-20}"
  show_section "$label"
  if [[ -f "$path" ]]; then
    tail -n "$lines" "$path"
  else
    echo "(missing: $path)"
  fi
}
