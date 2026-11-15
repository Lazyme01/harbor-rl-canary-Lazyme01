#!/bin/sh
cat > /app/reconcile.py <<'PY'
import csv
import json
import sys
from datetime import datetime
from decimal import Decimal

try:
    if len(sys.argv) != 2:
        raise ValueError("Expected one CSV filename")

    with open(sys.argv[1], newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        if next(reader, None) != ["tx_id", "timestamp", "amount", "status"]:
            raise ValueError("Invalid CSV header")

        total = Decimal("0")
        valid_count = 0
        failed_count = 0

        for row in reader:
            if not row:
                continue
            if len(row) != 4:
                raise ValueError("Invalid row")

            tx_id, timestamp, amount_text, status = row
            if not tx_id:
                raise ValueError("Empty transaction ID")

            dt = datetime.fromisoformat(timestamp)
            if dt.tzinfo is None or dt.utcoffset() is None:
                raise ValueError("Timezone required")

            amount = Decimal(amount_text)
            if not amount.is_finite() or amount < 0:
                raise ValueError("Invalid amount")

            if status not in ("success", "failed", "pending"):
                raise ValueError("Invalid status")

            if status == "success":
                total += amount
                valid_count += 1
            elif status == "failed":
                failed_count += 1

    print(json.dumps({
        "total_valid_amount": float(total),
        "valid_count": valid_count,
        "failed_count": failed_count
    }))

except Exception as error:
    print(str(error), file=sys.stderr)
    sys.exit(1)
PY
