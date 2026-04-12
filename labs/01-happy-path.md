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
python scripts/producer.py 20 --producer-id p1 --rate 2
```

## Inspect

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/inspect.sh
```

## What to notice

- the events stay in the stream history
- workers receive them through the consumer group
- each simulated side effect runs once
- each message is `XACK`ed and leaves pending
