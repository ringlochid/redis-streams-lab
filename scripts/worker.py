import os
import random
import time
import argparse

from redis.exceptions import ResponseError

from common import CHARGES_LOG, GROUP, SIMULATED_CHARGES_KEY, STREAM, redis_client

r = redis_client()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consume payment events from Redis Streams")
    p.add_argument("--consumer", default=os.getenv("CONSUMER", "worker-1"), help="Consumer name")
    p.add_argument("--group", default=GROUP, help="Consumer group name")
    p.add_argument("--batch", type=int, default=1, help="How many messages to read at once")
    p.add_argument("--block-ms", type=int, default=5000, help="Read block timeout")
    p.add_argument("--process-ms", type=int, default=0, help="Base processing delay per message (ms)")
    p.add_argument("--jitter-ms", type=int, default=0, help="Additional random processing jitter (ms)")
    p.add_argument(
        "--crash-after-side-effect",
        action="store_true",
        default=os.getenv("CRASH_AFTER_SIDE_EFFECT") == "1",
        help="Exit immediately after writing side effect (before XACK)",
    )
    return p.parse_args()


def ensure_group(group: str) -> None:
    try:
        r.xgroup_create(STREAM, group, id="0", mkstream=True)
        print(f"created consumer group {group}")
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def read_one(args: argparse.Namespace):
    pending = r.xreadgroup(args.group, args.consumer, {STREAM: "0"}, count=args.batch)
    if pending and pending[0][1]:
        return pending[0][1]

    fresh = r.xreadgroup(args.group, args.consumer, {STREAM: ">"}, count=args.batch, block=args.block_ms)
    if fresh and fresh[0][1]:
        return fresh[0][1]

    return []


def main() -> None:
    args = parse_args()
    ensure_group(args.group)
    print(
        f"worker={args.consumer} group={args.group} batch={args.batch} block={args.block_ms}ms "
        f"process_ms={args.process_ms} crash={args.crash_after_side_effect}"
    )

    while True:
        entries = read_one(args)
        if not entries:
            continue

        for msg_id, fields in entries:
            order_id = fields["order_id"]
            amount = fields["amount"]
            print(f"processing {msg_id} order={order_id} amount={amount}")

            # Simulated external side effect.
            with open(CHARGES_LOG, "a", encoding="utf-8") as f:
                f.write(
                    f"charged order={order_id} amount={amount} consumer={args.consumer} msg={msg_id}\n"
                )
            r.rpush(
                SIMULATED_CHARGES_KEY,
                f"order={order_id} amount={amount} consumer={args.consumer} msg={msg_id}",
            )

            if args.process_ms > 0:
                jitter = random.uniform(0, args.jitter_ms) if args.jitter_ms > 0 else 0.0
                time.sleep((args.process_ms + jitter) / 1000.0)

            if args.crash_after_side_effect:
                print("simulated crash before XACK")
                os._exit(1)

            r.xack(STREAM, args.group, msg_id)
            print(f"acked {msg_id}")


if __name__ == "__main__":
    main()
