import os

from redis.exceptions import ResponseError

from common import CHARGES_LOG, GROUP, SIMULATED_CHARGES_KEY, STREAM, redis_client

r = redis_client()

CONSUMER = os.getenv("CONSUMER", "worker-1")
CRASH_AFTER_SIDE_EFFECT = os.getenv("CRASH_AFTER_SIDE_EFFECT") == "1"


def ensure_group() -> None:
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        print(f"created consumer group {GROUP}")
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def read_one():
    pending = r.xreadgroup(GROUP, CONSUMER, {STREAM: "0"}, count=1)
    if pending and pending[0][1]:
        return pending[0][1]

    fresh = r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1, block=5000)
    if fresh and fresh[0][1]:
        return fresh[0][1]

    return []


ensure_group()
print(f"worker={CONSUMER} crash_after_side_effect={CRASH_AFTER_SIDE_EFFECT}")

while True:
    entries = read_one()
    if not entries:
        continue

    for msg_id, fields in entries:
        order_id = fields["order_id"]
        amount = fields["amount"]
        print(f"processing {msg_id} {fields}")

        with open(CHARGES_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"charged order={order_id} amount={amount} consumer={CONSUMER} msg={msg_id}\n"
            )
        r.rpush(
            SIMULATED_CHARGES_KEY,
            f"order={order_id} amount={amount} consumer={CONSUMER} msg={msg_id}",
        )

        if CRASH_AFTER_SIDE_EFFECT:
            print("simulated crash before XACK")
            os._exit(1)

        r.xack(STREAM, GROUP, msg_id)
        print(f"acked {msg_id}")
