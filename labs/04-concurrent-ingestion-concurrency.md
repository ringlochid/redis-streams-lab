# Lab 04 — Real streaming + concurrency

## Goal
Simulate a real stream: multiple producers and multiple consumers running at once.

You should see:
- entries arriving continuously
- workers consuming in parallel
- uneven split across consumers by Redis stream semantics
- clear evidence of scaling in the side-effect log

## 0) Start from a clean state

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/reset.sh
```

## 1) Start 3 consumers

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
CONSUMER=worker-1 python scripts/worker.py --batch 2 --process-ms 200 --consumer worker-1 > /tmp/w1.log 2>&1 &
CONSUMER=worker-2 python scripts/worker.py --batch 2 --process-ms 250 --consumer worker-2 > /tmp/w2.log 2>&1 &
CONSUMER=worker-3 python scripts/worker.py --batch 2 --process-ms 180 --consumer worker-3 > /tmp/w3.log 2>&1 &
```

(Optional sanity check)

```bash
docker compose exec redis redis-cli XPENDING payments payment-workers
```

## 2) Fire a sustained producer stream from 2 producers

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
python scripts/producer.py 100 --producer-id p1 --rate 6 --jitter-ms 80 > /tmp/p1.log 2>&1 &
python scripts/producer.py 100 --producer-id p2 --rate 6 --jitter-ms 80 --order-id "order-B" > /tmp/p2.log 2>&1 &
```

## 3) Watch what happened

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/inspect.sh
```

And stream logs:

```bash
tail -f /tmp/w1.log /tmp/w2.log /tmp/w3.log /tmp/p1.log /tmp/p2.log
```

## 4) Stop all background processes

In your terminal, kill the background jobs you started.

```bash
pkill -f "scripts/worker.py"
pkill -f "scripts/producer.py"
```

## What to watch for

- `producer p1` and `producer p2` are continuously appending events.
- Messages are not partitioned by producer; they are all in one stream `payments`.
- Worker logs should show interleaving consumption, not one worker doing everything.
- `simulated_charges` (and `data/charges.log`) should contain mixed `consumer=worker-*` entries.

This lab makes it clear your first setup is now closer to **real streaming input with concurrency**, not single-message toy behavior.
