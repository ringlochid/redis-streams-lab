import argparse
from collections import Counter
from typing import Iterable

from redis.exceptions import ResponseError

from common import GROUP, ORDER_STATE_PREFIX, ORDER_UPDATE_LOG_KEY, SIMULATED_CHARGES_KEY, STREAM, redis_client

r = redis_client()


def parse_kv_line(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in line.split():
        if "=" in token:
            k, v = token.split("=", 1)
            out[k] = v
    return out


def safe_xrange() -> list[tuple[str, dict[str, str]]]:
    try:
        return r.xrange(STREAM, "-", "+")
    except ResponseError:
        return []


def safe_group_info() -> dict:
    try:
        groups = r.xinfo_groups(STREAM)
    except ResponseError:
        return {}
    for g in groups:
        if g.get("name") == GROUP:
            return g
    return {}


def safe_list(key: str) -> list[str]:
    try:
        return r.lrange(key, 0, -1)
    except ResponseError:
        return []


def safe_order_state(order_id: str) -> dict[str, str]:
    try:
        return r.hgetall(f"{ORDER_STATE_PREFIX}{order_id}")
    except ResponseError:
        return {}


def consumer_counts(lines: Iterable[str]) -> Counter:
    counts: Counter = Counter()
    for line in lines:
        fields = parse_kv_line(line)
        consumer = fields.get("consumer")
        if consumer:
            counts[consumer] += 1
    return counts


def format_counts(counts: Counter) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))


def print_header(title: str) -> None:
    print(title)
    print("-" * len(title))


def summary_lab01() -> None:
    entries = safe_xrange()
    group = safe_group_info()
    charges = safe_list(SIMULATED_CHARGES_KEY)
    counts = consumer_counts(charges)
    pending = int(group.get("pending", 0)) if group else 0

    print_header("Lab 01 summary")
    print(f"Produced events: {len(entries)}")
    print(f"Side effects written: {len(charges)}")
    print(f"Consumers used: {format_counts(counts)}")
    print(f"Pending messages: {pending}")
    if len(entries) == len(charges) and pending == 0:
        print("Verdict: clean happy path — every produced event was consumed and acknowledged.")
    else:
        print("Verdict: unexpected — counts do not line up for a clean happy path.")


def summary_lab02() -> None:
    entries = safe_xrange()
    group = safe_group_info()
    charges = safe_list(SIMULATED_CHARGES_KEY)
    counts = consumer_counts(charges)
    pending = int(group.get("pending", 0)) if group else 0
    lag = int(group.get("lag", 0)) if group and group.get("lag") is not None else 0

    print_header("Lab 02 summary")
    print(f"Produced events: {len(entries)}")
    print(f"Side effects already written: {len(charges)}")
    print(f"Consumers used: {format_counts(counts)}")
    print(f"Pending messages: {pending}")
    print(f"Unread / lagging messages: {lag}")
    if len(charges) > 0 and pending > 0:
        print("Verdict: crash-before-ack reproduced — work happened, but Redis still considers at least one message unacknowledged.")
        print("Meaning: retry can run the same logical side effect again.")
    else:
        print("Verdict: crash pattern not clearly visible in this run.")


def summary_lab03() -> None:
    entries = safe_xrange()
    group = safe_group_info()
    charges = safe_list(SIMULATED_CHARGES_KEY)
    pending = int(group.get("pending", 0)) if group else 0
    order_counts = Counter()
    for line in charges:
        fields = parse_kv_line(line)
        order_id = fields.get("order")
        if order_id:
            order_counts[order_id] += 1
    duplicates = sum(v - 1 for v in order_counts.values() if v > 1)

    print_header("Lab 03 summary")
    print(f"Produced events: {len(entries)}")
    print(f"Total side effects written: {len(charges)}")
    print(f"Duplicate side effects observed: {duplicates}")
    print(f"Pending messages after recovery: {pending}")
    if duplicates > 0 and pending == 0:
        print("Verdict: reclaim worked — another worker recovered the stalled message, and the duplicate side effect shows the at-least-once tradeoff.")
    elif pending == 0:
        print("Verdict: recovery finished, but this run did not clearly show a duplicate side effect.")
    else:
        print("Verdict: recovery incomplete — pending work still exists.")


def summary_lab04() -> None:
    entries = safe_xrange()
    group = safe_group_info()
    charges = safe_list(SIMULATED_CHARGES_KEY)
    counts = consumer_counts(charges)
    pending = int(group.get("pending", 0)) if group else 0
    consumers = int(group.get("consumers", 0)) if group else 0

    print_header("Lab 04 summary")
    print(f"Produced events: {len(entries)}")
    print(f"Side effects written: {len(charges)}")
    print(f"Registered consumers in group: {consumers}")
    print(f"Observed work split: {format_counts(counts)}")
    print(f"Pending messages: {pending}")
    if len(counts) >= 2:
        print("Verdict: real concurrency observed — multiple workers shared the stream work.")
    else:
        print("Verdict: stream ran, but work split was weak in this run. Increase count/rate if you want stronger interleaving.")


def summary_lab05(order_id: str) -> None:
    entries = [fields for _, fields in safe_xrange() if fields.get("event") == "order_delta" and fields.get("order_id") == order_id]
    logs = safe_list(ORDER_UPDATE_LOG_KEY)
    state = safe_order_state(order_id)
    counts = consumer_counts(logs)
    expected = sum(int(e.get("delta", "0")) for e in entries)
    balance = int(state.get("balance", "0")) if state else 0
    modes = sorted({line.split()[0] for line in logs if line.strip()})

    print_header("Lab 05 summary")
    print(f"Hot order id: {order_id}")
    print(f"Produced delta events: {len(entries)}")
    print(f"Observed workers: {format_counts(counts)}")
    print(f"Mode(s): {', '.join(modes) if modes else 'none'}")
    print(f"Expected total delta: {expected}")
    print(f"Final stored balance: {balance}")
    if balance == expected:
        if "atomic" in modes:
            print("Verdict: atomic fix worked — final balance matches the true total delta.")
        else:
            print("Verdict: this naive run happened to end correctly. Rerun with higher counts/jitter if you want the race to show up harder.")
    else:
        print("Verdict: lost update reproduced — naive shared-state writes did not preserve the true total delta.")


def main() -> None:
    p = argparse.ArgumentParser(description="Print a compact human summary for a Redis Streams lab run")
    p.add_argument("lab", choices=["lab01", "lab02", "lab03", "lab04", "lab05"])
    p.add_argument("--hot-order-id", default="order-hot-main")
    args = p.parse_args()

    if args.lab == "lab01":
        summary_lab01()
    elif args.lab == "lab02":
        summary_lab02()
    elif args.lab == "lab03":
        summary_lab03()
    elif args.lab == "lab04":
        summary_lab04()
    else:
        summary_lab05(args.hot_order_id)


if __name__ == "__main__":
    main()
