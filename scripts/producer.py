import argparse
import random
import time

from common import STREAM, redis_client

r = redis_client()


def looks_like_int(v: str) -> bool:
    try:
        int(v)
        return True
    except Exception:
        return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Produce events into Redis Streams")
    p.add_argument("args", nargs="*", help="Legacy positional: [count] [base_amount|base_id]")
    p.add_argument("--producer-id", "-p", default="p1", help="Producer label")
    p.add_argument("--rate", "-r", type=float, default=0.0, help="Events per second (0 = no pacing)")
    p.add_argument("--jitter-ms", type=int, default=0, help="Max extra random jitter per event (ms)")
    p.add_argument("--amount-min", type=int, default=20, help="Random amount lower bound (payment mode)")
    p.add_argument("--amount-max", type=int, default=500, help="Random amount upper bound (payment mode)")

    p.add_argument("--mode", choices=["payment", "order_update"], default="payment", help="event payload shape")
    p.add_argument("--hot-order-id", default="order-hot", help="Fixed order id for order_update mode")
    p.add_argument("--seq-start", type=int, default=1, help="Starting sequence for order_update mode (local mode)")
    p.add_argument("--delta-min", type=int, default=-40, help="Random delta lower bound (order_update mode)")
    p.add_argument("--delta-max", type=int, default=100, help="Random delta upper bound (order_update mode)")
    p.add_argument("--shared-seq", action="store_true", help="Use Redis-backed shared sequence counter for order_update mode")

    return p.parse_args()


def infer_positional(args: argparse.Namespace):
    count = 1
    base_id = f"evt-{int(time.time())}"
    amount = 100

    if args.args:
        first = args.args[0]
        if looks_like_int(first):
            count = int(first)
            if len(args.args) >= 2 and looks_like_int(args.args[1]):
                amount = int(args.args[1])
        else:
            base_id = first
            if len(args.args) >= 2 and looks_like_int(args.args[1]):
                amount = int(args.args[1])

    return count, base_id, amount


def produce_payment(args: argparse.Namespace, count: int, base_id: str, amount: int):
    interval_ms = 0.0 if args.rate <= 0 else 1000.0 / args.rate
    sent = 0
    while True:
        if count != 0 and sent >= count:
            break

        sent += 1
        amt = amount
        if args.amount_min <= args.amount_max:
            amt = random.randint(args.amount_min, args.amount_max)
        order_id = f"{base_id}:{args.producer_id}:{sent}"

        msg_id = r.xadd(
            STREAM,
            {
                "event": "payment_requested",
                "order_id": order_id,
                "amount": str(amt),
                "producer": args.producer_id,
                "ts": str(time.time()),
            },
        )

        print(f"XADD {STREAM} {msg_id} producer={args.producer_id} seq={sent} amount={amt} order_id={order_id}")

        if interval_ms > 0:
            sleep = interval_ms / 1000.0
            if args.jitter_ms > 0:
                sleep += random.uniform(0, args.jitter_ms / 1000.0)
            time.sleep(sleep)


def produce_order_updates(args: argparse.Namespace, count: int):
    interval_ms = 0.0 if args.rate <= 0 else 1000.0 / args.rate
    sent = 0
    local_seq = args.seq_start
    counter_key = f"{args.hot_order_id}:seq_counter"

    while True:
        if count != 0 and sent >= count:
            break

        sent += 1
        if args.shared_seq:
            seq = r.incr(counter_key)
        else:
            seq = local_seq
            local_seq += 1

        delta = random.randint(args.delta_min, args.delta_max)
        msg_id = r.xadd(
            STREAM,
            {
                "event": "order_delta",
                "order_id": args.hot_order_id,
                "seq": str(seq),
                "delta": str(delta),
                "producer": args.producer_id,
                "ts": str(time.time()),
            },
        )
        print(
            f"XADD {STREAM} {msg_id} order={args.hot_order_id} producer={args.producer_id} seq={seq} delta={delta}"
        )

        if interval_ms > 0:
            sleep = interval_ms / 1000.0
            if args.jitter_ms > 0:
                sleep += random.uniform(0, args.jitter_ms / 1000.0)
            time.sleep(sleep)


def main() -> None:
    args = parse_args()
    count, base_id, amount = infer_positional(args)

    target = "forever" if count == 0 else str(count)
    print(f"producer={args.producer_id} mode={args.mode} stream={STREAM} count={target} rate={args.rate or 'unlimited'}")

    if args.mode == "order_update":
        produce_order_updates(args, count)
    else:
        produce_payment(args, count, base_id, amount)


if __name__ == "__main__":
    main()
