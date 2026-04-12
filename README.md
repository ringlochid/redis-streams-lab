# Redis Streams Lab

Small, visible experiments for learning Redis Streams failure semantics.

## Layout

```text
redis-streams-lab/
├── docker-compose.yml
├── requirements.txt
├── data/
├── labs/
│   ├── 01-happy-path.md
│   ├── 02-crash-before-ack.md
│   └── 03-reclaim-and-retry.md
└── scripts/
    ├── common.py
    ├── inspect.sh
    ├── producer.py
    ├── reset.sh
    └── worker.py
```

## One-time setup

```bash
cd ~/leo/experiments/redis-streams-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d
chmod +x scripts/*.sh
```

## Run order

1. `labs/01-happy-path.md`
2. `labs/02-crash-before-ack.md`
3. `labs/03-reclaim-and-retry.md`

## Helper commands

Reset lab state:

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/reset.sh
```

Inspect current Redis + side-effect state:

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/inspect.sh
```

## What this lab is teaching

- `XADD` appends an event
- `XREADGROUP` delivers work to one consumer in a group
- `XACK` marks a message as processed
- `XPENDING` shows delivered-but-not-acked work
- `XAUTOCLAIM` reassigns stalled work
- at-least-once delivery duplicates non-idempotent side effects unless you add a fix

## Not included yet

This first cut is intentionally simple.

No Postgres, FastAPI, or Celery yet.
Those come later when you want to learn:

- outbox pattern
- idempotency table
- API producer integration
- transaction boundaries
