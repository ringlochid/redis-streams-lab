import argparse
import os
import random
import time

from redis.exceptions import ResponseError

from common import GROUP, ORDER_STATE_PREFIX, ORDER_UPDATE_LOG_KEY, STREAM, redis_client

r = redis_client()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consume order_delta events and update shared order state")
    p.add_argument("--consumer", default=os.getenv("CONSUMER", "worker-1"), help="Consumer name")
    p.add_argument("--group", default=GROUP, help="Consumer group name")
    p.add_argument("--batch", type=int, default=1, help="How many messages to read at once")
    p.add_argument("--block-ms", type=int, default=5000, help="Read block timeout")
    p.add_argument("--process-ms", type=int, default=0, help="Base processing delay per message (ms)")
    p.add_argument("--jitter-ms", type=int, default=0, help="Additional random processing jitter (ms)")
    p.add_argument(
        "--mode",
        choices=["naive", "atomic"],
        default="naive",
        help="naive = read-modify-write; atomic = Lua-wrapped atomic increment",
    )
    p.add_argument(
        "--skip-non-updates",
        action="store_true",
        help="Skip events where event != order_delta instead of failing",
    )
    return p.parse_args()


def ensure_group(group: str) -> None:
    try:
        r.xgroup_create(STREAM, group, id="0", mkstream=True)
        print(f"created consumer group {group}")
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def read_batch(args: argparse.Namespace):
    pending = r.xreadgroup(args.group, args.consumer, {STREAM: "0"}, count=args.batch)
    if pending and pending[0][1]:
        return pending[0][1]

    fresh = r.xreadgroup(args.group, args.consumer, {STREAM: ">"}, count=args.batch, block=args.block_ms)
    if fresh and fresh[0][1]:
        return fresh[0][1]

    return []


def delay(args: argparse.Namespace) -> None:
    if args.process_ms > 0:
        jitter = random.uniform(0, args.jitter_ms / 1000.0) if args.jitter_ms > 0 else 0.0
        time.sleep((args.process_ms / 1000.0) + jitter)


def log_line(kind: str, msg_id: str, order_id: str, seq: str, delta: str, before: str, after: str, info: str = "") -> str:
    parts = [
        kind,
        f"msg={msg_id}",
        f"order={order_id}",
        f"seq={seq}",
        f"delta={delta}",
        f"before={before}",
        f"after={after}",
        info,
    ]
    return " ".join([p for p in parts if p])


ATOMIC_LUA = """
local state_key = KEYS[1]
local incoming_seq = tonumber(ARGV[1])
local incoming_delta = tonumber(ARGV[2])
local msg_id = ARGV[3]
local consumer = ARGV[4]
local ts = ARGV[5]

local before = tonumber(redis.call('HGET', state_key, 'balance') or '0')
local cur_seq = tonumber(redis.call('HGET', state_key, 'seq') or '0')
local after = before + incoming_delta
local max_seq = cur_seq
if incoming_seq > cur_seq then
  max_seq = incoming_seq
end

redis.call('HSET', state_key,
  'balance', after,
  'seq', max_seq,
  'last_msg', msg_id,
  'consumer', consumer,
  'updated_at', ts
)

return {before, after, max_seq}
"""


def apply_naive(order_id: str, seq: str, delta: int, msg_id: str, consumer: str, args: argparse.Namespace):
    state_key = f"{ORDER_STATE_PREFIX}{order_id}"
    state = r.hgetall(state_key)
    before = int(state.get("balance", "0"))
    before_seq = int(state.get("seq", "0"))

    delay(args)

    after = before + delta
    r.hset(
        state_key,
        mapping={"balance": str(after), "seq": seq, "consumer": consumer, "last_msg": msg_id},
    )

    r.rpush(
        ORDER_UPDATE_LOG_KEY,
        log_line(
            "naive",
            msg_id,
            order_id,
            seq,
            str(delta),
            str(before),
            str(after),
            f"consumer={consumer} prev_seq={before_seq}",
        ),
    )


def apply_atomic(order_id: str, seq: str, delta: int, msg_id: str, consumer: str, args: argparse.Namespace):
    state_key = f"{ORDER_STATE_PREFIX}{order_id}"
    delay(args)
    before, after, max_seq = r.eval(ATOMIC_LUA, 1, state_key, seq, str(delta), msg_id, consumer, str(time.time()))

    r.rpush(
        ORDER_UPDATE_LOG_KEY,
        log_line(
            "atomic",
            msg_id,
            order_id,
            seq,
            str(delta),
            str(before),
            str(after),
            f"consumer={consumer} max_seq={max_seq}",
        ),
    )


def main() -> None:
    args = parse_args()
    ensure_group(args.group)
    print(
        f"order_worker={args.consumer} mode={args.mode} batch={args.batch} "
        f"process_ms={args.process_ms} jitter={args.jitter_ms}"
    )

    while True:
        entries = read_batch(args)
        if not entries:
            continue

        for msg_id, fields in entries:
            event = fields.get("event", "")
            if event != "order_delta":
                if args.skip_non_updates:
                    r.xack(STREAM, args.group, msg_id)
                    print(f"skip_non_update {msg_id} event={event}")
                    continue
                print(f"unexpected event={event} msg={msg_id}")
                continue

            order_id = fields["order_id"]
            seq = fields["seq"]
            delta = int(fields["delta"])

            if args.mode == "naive":
                apply_naive(order_id, seq, delta, msg_id, args.consumer, args)
            else:
                apply_atomic(order_id, seq, delta, msg_id, args.consumer, args)

            r.xack(STREAM, args.group, msg_id)
            print(f"processed order={order_id} seq={seq} delta={delta} mode={args.mode}")


if __name__ == "__main__":
    main()
