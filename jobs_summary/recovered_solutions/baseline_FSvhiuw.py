#!/usr/bin/env python3
"""Reconcile a CSV of transactions.

The script validates the input CSV according to the specification and prints a
JSON summary.  Any validation error results in a non‑zero exit status and an
error message on stderr.
"""

import sys
import csv
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

ALLOWED_STATUS = {"success", "failed", "pending"}
EXPECTED_HEADER = ["tx_id", "timestamp", "amount", "status"]


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO‑8601 timestamp that must include timezone info.

    The ISO format may end with "Z" to indicate UTC; we replace it with
    "+00:00" for datetime.fromisoformat compatibility.
    """
    # Support trailing Z for UTC
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return dt


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        print("Usage: python3 reconcile.py INPUT.csv", file=sys.stderr)
        sys.exit(2)

    csv_path = argv[0]
    try:
        f = open(csv_path, newline="", encoding="utf-8-sig")
    except OSError as e:
        print(f"Error opening file: {e}", file=sys.stderr)
        sys.exit(2)

    with f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print("CSV file is empty", file=sys.stderr)
            sys.exit(1)
        if header != EXPECTED_HEADER:
            print("Invalid CSV header", file=sys.stderr)
            sys.exit(1)

        best_rows = {}
        line_number = 1  # header is line 1
        for raw_row in reader:
            line_number += 1
            # Skip blank lines (all cells empty or whitespace)
            if not any(cell.strip() for cell in raw_row):
                continue
            if len(raw_row) != 4:
                print(f"Invalid row length on line {line_number}", file=sys.stderr)
                sys.exit(1)
            tx_id, ts_str, amount_str, status = raw_row
            if not tx_id:
                print(f"Empty transaction ID on line {line_number}", file=sys.stderr)
                sys.exit(1)
            try:
                ts = parse_timestamp(ts_str)
            except Exception as e:
                print(f"Invalid timestamp on line {line_number}: {e}", file=sys.stderr)
                sys.exit(1)
            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                print(f"Invalid amount on line {line_number}", file=sys.stderr)
                sys.exit(1)
            if amount.is_nan() or amount.is_infinite() or amount < 0:
                print(f"Amount must be a finite non‑negative decimal on line {line_number}", file=sys.stderr)
                sys.exit(1)
            if status not in ALLOWED_STATUS:
                print(f"Invalid status on line {line_number}", file=sys.stderr)
                sys.exit(1)

            utc_ts = ts.astimezone(timezone.utc)
            existing = best_rows.get(tx_id)
            if existing is None:
                best_rows[tx_id] = {
                    "ts": utc_ts,
                    "amount": amount,
                    "status": status,
                    "order": line_number,
                }
            else:
                # Keep later timestamp, or later line if timestamps equal
                if utc_ts > existing["ts"] or (utc_ts == existing["ts"] and line_number > existing["order"]):
                    best_rows[tx_id] = {
                        "ts": utc_ts,
                        "amount": amount,
                        "status": status,
                        "order": line_number,
                    }

    total = Decimal('0')
    valid_count = 0
    failed_count = 0
    for rec in best_rows.values():
        total += rec["amount"]
        if rec["status"] == "success":
            valid_count += 1
        elif rec["status"] == "failed":
            failed_count += 1
        # pending rows contribute to total but not to the two counts

    result = {
        "total_valid_amount": float(total),
        "valid_count": valid_count,
        "failed_count": failed_count,
    }
    print(json.dumps(result))
    sys.exit(0)

if __name__ == "__main__":
    main()
