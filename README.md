# Redis Streams Lab

You are now using **single-command lab runs** with compact results.

- Run one script per lab.
- Each script prints a concise **Verdict** first.
- Full raw logs are still written to `/tmp`, on demand.
- To view full raw output, run with `LAB_VERBOSE=1`.

---

## One-time setup

```bash
cd ~/leo/experiments/redis-streams-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x scripts/*.sh
```

---

## Quick flow (recommended)

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/run_lab01.sh
./scripts/run_lab02.sh
./scripts/run_lab03.sh
./scripts/run_lab04.sh
./scripts/run_lab05_naive.sh
./scripts/run_lab05_atomic.sh
```

Each command:
- resets Redis for that lab
- starts Redis if needed
- starts worker(s) + producer(s)
- runs `MONITOR` capture
- prints a compact summary + log tails

For Labs 01–04, payment events now use ids like `evt-<run_ts>:<producer>:<seq>` so they read as event/batch ids instead of looking like one shared business order.

---

## Lab commands

### Lab 01 — happy path

```bash
./scripts/run_lab01.sh
```

### Lab 02 — crash before `XACK`

```bash
./scripts/run_lab02.sh
```

### Lab 03 — reclaim and retry

```bash
./scripts/run_lab03.sh
```

### Lab 04 — real concurrency

```bash
./scripts/run_lab04.sh
```

### Lab 05 — hot-key contention

```bash
./scripts/run_lab05_naive.sh
./scripts/run_lab05_atomic.sh
```

Optional: tune counts/rate

```bash
LAB04_COUNT=100 LAB04_RATE=10 ./scripts/run_lab04.sh
HOT_ORDER_ID=order-hot-main LAB05_COUNT=120 LAB05_RATE=16 ./scripts/run_lab05_naive.sh
HOT_ORDER_ID=order-hot-main LAB05_COUNT=120 LAB05_RATE=16 ./scripts/run_lab05_atomic.sh
```

Want raw logs?

```bash
LAB_VERBOSE=1 ./scripts/run_lab01.sh
```

---

## How to read the output (short)

Every run prints one of these quick verdict lines.

- **Lab 01:** `clean happy path` means produced = consumed, no pending.
- **Lab 02:** `crash-before-ack` means side effects happened but pending messages still exist. The script now also prints a tiny proof block showing `side effect happened` + `ack not found`.
- **Lab 03:** `reclaim worked` means another worker recovered the stalled event; duplicates are possible. The script now also prints a tiny proof block showing the same message id causing two side effects.
- **Lab 04:** `real concurrency observed` means work is actually split across multiple workers.
- **Lab 05:** `atomic fix worked` means final aggregate equals expected. `lost update reproduced` means naive path dropped updates.

---

### Where raw logs are written

| Lab | logs |
|---|---|
| Lab 01 | `/tmp/lab01_monitor.log`, `/tmp/lab01_worker.log`, `/tmp/lab01_producer.log` |
| Lab 02 | `/tmp/lab02_monitor.log`, `/tmp/lab02_worker.log`, `/tmp/lab02_producer.log` |
| Lab 03 | `/tmp/lab03_monitor.log`, `/tmp/lab03_worker1.log`, `/tmp/lab03_worker2.log`, `/tmp/lab03_producer.log`, `/tmp/lab03_claim.log` |
| Lab 04 | `/tmp/lab04_monitor.log`, `/tmp/lab04_w1.log`, `/tmp/lab04_w2.log`, `/tmp/lab04_w3.log`, `/tmp/lab04_p1.log`, `/tmp/lab04_p2.log` |
| Lab 05 naive | `/tmp/lab05_naive_monitor.log`, `/tmp/lab05_naive_w1.log`, `/tmp/lab05_naive_w2.log`, `/tmp/lab05_naive_pA.log`, `/tmp/lab05_naive_pB.log` |
| Lab 05 atomic | `/tmp/lab05_atomic_monitor.log`, `/tmp/lab05_atomic_w1.log`, `/tmp/lab05_atomic_w2.log`, `/tmp/lab05_atomic_pA.log`, `/tmp/lab05_atomic_pB.log` |

---

## Common issue: `service "redis" is not running`

Start it:

```bash
docker compose up -d redis
```

If a container exits and all scripts still fail, restart and then rerun the lab script.
