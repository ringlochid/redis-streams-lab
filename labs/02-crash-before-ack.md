# Lab 02 — Crash before XACK

## Goal
Reproduce the classic at-least-once failure:

side effect succeeds, worker dies, message is still pending

## Reset first

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/reset.sh
```

## Terminal 1

```bash
cd ~/leo/experiments/redis-streams-lab
docker compose exec redis redis-cli MONITOR
```

## Terminal 2

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
CRASH_AFTER_SIDE_EFFECT=1 python scripts/worker.py
```

## Terminal 3

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
python scripts/producer.py order-2 250
```

## Inspect

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/inspect.sh
```

## What to notice

- the side effect already happened once
- the message was never acknowledged
- Redis still shows it as pending
- this is why retries can duplicate external actions
