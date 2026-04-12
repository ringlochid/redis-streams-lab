# Lab 03 — Reclaim and retry

## Goal
Take a stalled pending message and hand it to another worker.

## Prerequisite
Run Lab 02 first so there is a pending message.

## Reclaim the message

```bash
cd ~/leo/experiments/redis-streams-lab
docker compose exec redis redis-cli XAUTOCLAIM payments payment-workers worker-2 0 0-0 COUNT 10
```

## Run a second worker

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
CONSUMER=worker-2 python scripts/worker.py
```

## Inspect again

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/inspect.sh
```

## What to notice

- another consumer can reclaim stalled work
- the same logical payment can now appear twice in the side-effect log
- this is correct for at-least-once delivery, but dangerous for non-idempotent actions
