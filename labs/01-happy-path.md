# Lab 01 — Happy path

## Goal
See the normal lifecycle:

`XADD -> XREADGROUP -> side effect -> XACK`

## Terminal 1

```bash
cd ~/leo/experiments/redis-streams-lab
docker compose exec redis redis-cli MONITOR
```

## Terminal 2

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
python scripts/worker.py
```

## Terminal 3

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
python scripts/producer.py order-1 100
```

## Inspect

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/inspect.sh
```

## What to notice

- the event stays in the stream history
- the worker receives it through the consumer group
- the simulated side effect runs once
- `XACK` removes it from pending
