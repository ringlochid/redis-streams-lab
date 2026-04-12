# Redis Streams Lab

Small, visible experiments for learning Redis Streams failure semantics and concurrency behavior.

## Layout

```text
redis-streams-lab/
├── docker-compose.yml
├── requirements.txt
├── data/
├── labs/
│   ├── 01-happy-path.md
│   ├── 02-crash-before-ack.md
│   ├── 03-reclaim-and-retry.md
│   ├── 04-concurrent-ingestion-concurrency.md
│   ├── 05-hot-key-race-contested-order.md
│
└── scripts/
    ├── common.py
    ├── inspect.sh
    ├── order_worker.py
    ├── producer.py
    ├── reset.sh
    ├── run_lab05_atomic.sh
    ├── run_lab05_naive.sh
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
4. `labs/04-concurrent-ingestion-concurrency.md`
5. `labs/05-hot-key-race-contested-order.md`

## Lab 05 one-command runs

```bash
cd ~/leo/experiments/redis-streams-lab

# see naive race (do this first)
HOT_ORDER_ID=order-hot-main LAB05_COUNT=80 ./scripts/run_lab05_naive.sh

# see fixed behavior with atomic increment
HOT_ORDER_ID=order-hot-main LAB05_COUNT=80 ./scripts/run_lab05_atomic.sh
```

You can tweak speed by overriding:
- `LAB05_RATE` (events/sec, default 12)
- `LAB05_JITTER_MS` (producer jitter, default 80)
- `LAB05_UPDATE_MS` (worker delay, default 120)
- `LAB05_WORKER_JITTER_MS` (worker jitter, default 200)

## Helper commands

Reset lab state:

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/reset.sh
```

Inspect current Redis + side-effect state:

```bash
cd ~/leo/experiments/redis-streams-lab
HOT_ORDER_ID=order-hot-main ./scripts/inspect.sh
```

## What this lab is teaching

- `XADD` appends an event
- `XREADGROUP` delivers work to one consumer in a group
- `XACK` marks a message as processed
- `XPENDING` shows delivered-but-not-acked work
- `XAUTOCLAIM` reassigns stalled work
- at-least-once delivery duplicates non-idempotent side effects unless you add a fix
- parallel consumers can create **write contention** on shared state when processing one hot key
- naive read-modify-write can lose updates under contention
- atomic Lua updates protect shared numeric state from races

## Not included yet

This first cut is intentionally simple.

No Postgres, FastAPI, or Celery yet.
Those come later when you want to learn:

- outbox pattern
- idempotency table
- API producer integration
- transaction boundaries
