import sys
import time

from common import STREAM, redis_client

r = redis_client()

order_id = sys.argv[1] if len(sys.argv) > 1 else f"order-{int(time.time())}"
amount = sys.argv[2] if len(sys.argv) > 2 else "100"

msg_id = r.xadd(
    STREAM,
    {
        "event": "payment_requested",
        "order_id": order_id,
        "amount": amount,
        "ts": str(time.time()),
    },
)

print(f"XADD {STREAM} {msg_id} order_id={order_id} amount={amount}")
