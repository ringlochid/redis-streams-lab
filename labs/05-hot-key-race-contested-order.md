# Lab 05 — Hot-key contention: out-of-order updates under parallel consumers

## Goal
Drive multiple producers into the same hot order key so two consumers process interleaving updates.

You will see:
- naïve read-modify-write loses updates
- atomic update mode keeps the numeric balance consistent under contention

---

## One-command run (recommended)

### Naive mode (expected to show wrong final state)

```bash
cd ~/leo/experiments/redis-streams-lab
HOT_ORDER_ID=order-hot-main LAB05_COUNT=80 ./scripts/run_lab05_naive.sh
```

### Atomic mode (fix)

```bash
cd ~/leo/experiments/redis-streams-lab
HOT_ORDER_ID=order-hot-main LAB05_COUNT=80 ./scripts/run_lab05_atomic.sh
```

The one-command scripts:
- launch two workers and two producers
- wait until both producers finish
- print inspection output
- print expected delta sum computed from producer logs

## Manual walkthrough (what the script is doing)

### Step 1 — Reset and choose a target order

```bash
cd ~/leo/experiments/redis-streams-lab
./scripts/reset.sh
export HOT_ORDER_ID=order-hot-main
```

### Step 2 — Start two consumers in naive mode

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
python scripts/order_worker.py --mode naive --consumer worker-1 --batch 2 --process-ms 120 --jitter-ms 200 > /tmp/order_w1.log 2>&1 &
python scripts/order_worker.py --mode naive --consumer worker-2 --batch 2 --process-ms 120 --jitter-ms 200 > /tmp/order_w2.log 2>&1 &
```

### Step 3 — Emit hot updates for one order

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
python scripts/producer.py 80 --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate 12 --jitter-ms 80 -p pA > /tmp/pA.log 2>&1
python scripts/producer.py 80 --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate 12 --jitter-ms 80 -p pB > /tmp/pB.log 2>&1
```

### Step 4 — Inspect

```bash
cd ~/leo/experiments/redis-streams-lab
HOT_ORDER_ID=order-hot-main ./scripts/inspect.sh
```

Also read logs:

```bash
tail -n 40 /tmp/order_w1.log /tmp/order_w2.log /tmp/pA.log /tmp/pB.log
```

### Why this happens

`order_delta` events are additive (`balance += delta`).
In naive mode, each worker does:
1) read current balance,
2) wait,
3) write new balance.

With concurrent consumers, those reads can overlap and overwrite each other.

### Fix: atomic mode

Now replay the same scenario with `--mode atomic`.

```bash
cd ~/leo/experiments/redis-streams-lab
source .venv/bin/activate
python scripts/order_worker.py --mode atomic --consumer worker-1 --batch 2 --process-ms 120 --jitter-ms 200 > /tmp/order_w1_g.log 2>&1 &
python scripts/order_worker.py --mode atomic --consumer worker-2 --batch 2 --process-ms 120 --jitter-ms 200 > /tmp/order_w2_g.log 2>&1 &

python scripts/producer.py 80 --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate 12 --jitter-ms 80 -p pA > /tmp/pA_g.log 2>&1
python scripts/producer.py 80 --mode order_update --shared-seq --hot-order-id "$HOT_ORDER_ID" --rate 12 --jitter-ms 80 -p pB > /tmp/pB_g.log 2>&1
```

Inspect again:

```bash
cd ~/leo/experiments/redis-streams-lab
HOT_ORDER_ID=order-hot-main ./scripts/inspect.sh
```

Expected result:
- final `order_state:order-hot-main` balance should match the total delta sum for this run
- no overwrite-loss from race in the same worker group

Optional cleanup:

```bash
pkill -f "scripts/order_worker.py"
pkill -f "scripts/producer.py"
```

## Limits of this lab

Atomic increment fixes overwrite races, but does **not** by itself solve duplicates from retries. For that, you still need idempotency keys.
