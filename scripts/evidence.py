import argparse
import re
from collections import defaultdict

from redis.exceptions import ResponseError

from common import GROUP, SIMULATED_CHARGES_KEY, STREAM, redis_client

r = redis_client()
TOKEN_RE = re.compile(r'"([^"]*)"')


def parse_kv_line(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in line.split():
        if "=" in token:
            k, v = token.split("=", 1)
            out[k] = v
    return out


def safe_list(key: str) -> list[str]:
    try:
        return r.lrange(key, 0, -1)
    except ResponseError:
        return []


def safe_pending() -> int:
    try:
        groups = r.xinfo_groups(STREAM)
    except ResponseError:
        return 0
    for g in groups:
        if g.get("name") == GROUP:
            return int(g.get("pending", 0))
    return 0


def parse_monitor(path: str):
    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                tokens = TOKEN_RE.findall(line)
                if not tokens:
                    continue
                events.append((line, tokens[0], tokens[1:]))
    except FileNotFoundError:
        pass
    return events


def first_line_matching(events, predicate):
    for line, cmd, args in events:
        if predicate(cmd, args):
            return line
    return None


def lines_matching(events, predicate):
    out = []
    for line, cmd, args in events:
        if predicate(cmd, args):
            out.append(line)
    return out


def print_lab02(monitor_log: str) -> None:
    charges = safe_list(SIMULATED_CHARGES_KEY)
    events = parse_monitor(monitor_log)
    pending = safe_pending()

    print("Lab 02 key evidence")
    print("-------------------")

    if not charges:
        print("No side effect lines found.")
        return

    first_charge = charges[0]
    fields = parse_kv_line(first_charge)
    msg_id = fields.get("msg", "?")

    xack = first_line_matching(events, lambda cmd, args: cmd == "XACK" and msg_id in args)

    print(f"Side effect happened: {first_charge}")
    print(f"Ack for same msg id: {'NOT FOUND' if xack is None else xack}")
    print(f"Group pending count: {pending}")
    print("Meaning: business effect happened, but queue completion did not. Retry can repeat the same logical action.")


def print_lab03(monitor_log: str) -> None:
    charges = safe_list(SIMULATED_CHARGES_KEY)
    events = parse_monitor(monitor_log)

    by_msg: dict[str, list[str]] = defaultdict(list)
    for line in charges:
        fields = parse_kv_line(line)
        msg_id = fields.get("msg")
        if msg_id:
            by_msg[msg_id].append(line)

    dup_msg = None
    dup_lines: list[str] = []
    for msg_id, lines in by_msg.items():
        if len(lines) > 1:
            dup_msg = msg_id
            dup_lines = lines
            break

    print("Lab 03 key evidence")
    print("-------------------")

    if dup_msg is None:
        print("No duplicate side effect found in this run.")
        return

    claim_line = first_line_matching(events, lambda cmd, args: cmd == "XAUTOCLAIM")
    xack_lines = lines_matching(events, lambda cmd, args: cmd == "XACK" and dup_msg in args)

    print("Same message produced side effect twice:")
    for line in dup_lines:
        print(f"- {line}")
    print(f"Reclaim step: {claim_line if claim_line else 'NOT FOUND'}")
    if xack_lines:
        print(f"Final ack after replay: {xack_lines[-1]}")
    else:
        print("Final ack after replay: NOT FOUND")
    print("Meaning: worker-1 did the effect and died before ack; worker-2 reclaimed the same message and did the effect again, then acked it.")


def main() -> None:
    p = argparse.ArgumentParser(description="Print compact proof lines for crash/retry labs")
    p.add_argument("lab", choices=["lab02", "lab03"])
    p.add_argument("--monitor-log", required=True)
    args = p.parse_args()

    if args.lab == "lab02":
        print_lab02(args.monitor_log)
    else:
        print_lab03(args.monitor_log)


if __name__ == "__main__":
    main()
