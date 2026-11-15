Repair `/app/reconcile.py` so it reconciles a CSV file. Run it as:

```text
python3 /app/reconcile.py INPUT.csv
```

The CSV header must be exactly `tx_id,timestamp,amount,status`. Ignore blank
lines. Each other row must have a nonempty transaction ID, a timezone-aware
ISO 8601 timestamp, a finite nonnegative decimal amount, and a status exactly
equal to `success`, `failed`, or `pending`. Invalid headers or rows must cause
a nonzero exit status and an error on standard error.

Treat transaction IDs as case-sensitive. For each ID, keep the row with the
latest timestamp by its UTC instant; when instants are equal, the later CSV row
wins. From those retained rows, sum amounts and count rows whose status is
`success`; count rows whose status is `failed` separately. Ignore `pending`
rows. Print one JSON object to standard output with numeric fields
`total_valid_amount`, `valid_count`, and `failed_count`.
