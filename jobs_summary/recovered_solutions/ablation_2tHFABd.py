import sys, csv, json, decimal, datetime, re

def parse_timestamp(ts):
    # Parse ISO8601 with timezone, convert to UTC datetime
    # datetime.fromisoformat handles offsets in Python 3.11+, fallback with regex
    try:
        dt = datetime.datetime.fromisoformat(ts)
    except Exception:
        # Simple regex for ISO8601 with Z or offset
        m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:\d{2})$", ts)
        if not m:
            raise ValueError('Invalid timestamp')
        base, offset = m.groups()
        dt = datetime.datetime.fromisoformat(base)
        if offset == 'Z':
            tz = datetime.timezone.utc
        else:
            sign = 1 if offset[0] == '+' else -1
            hours, minutes = map(int, offset[1:].split(':'))
            tz = datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))
        dt = dt.replace(tzinfo=tz)
    if dt.tzinfo is None:
        raise ValueError('Timestamp not timezone-aware')
    return dt.astimezone(datetime.timezone.utc)

def is_finite_decimal(val):
    try:
        d = decimal.Decimal(val)
    except Exception:
        return False
    if not d.is_finite():
        return False
    if d < 0:
        return False
    return True

def main():
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: python3 reconcile.py INPUT.csv\n')
        sys.exit(2)
    path = sys.argv[1]
    try:
        f = open(path, newline='')
    except Exception as e:
        sys.stderr.write(f'Could not open file: {e}\n')
        sys.exit(2)
    reader = csv.reader(f)
    try:
        header = next(reader)
    except StopIteration:
        sys.stderr.write('Empty file\n')
        sys.exit(1)
    if header != ['tx_id', 'timestamp', 'amount', 'status']:
        sys.stderr.write('Invalid header\n')
        sys.exit(1)
    records = {}
    failed_count = 0
    for line_num, row in enumerate(reader, start=2):
        if not row or all(cell.strip() == '' for cell in row):
            continue  # ignore blank lines
        if len(row) != 4:
            sys.stderr.write(f'Row {line_num}: incorrect number of columns\n')
            sys.exit(1)
        tx_id, ts_str, amt_str, status = row
        if tx_id == '':
            sys.stderr.write(f'Row {line_num}: empty transaction ID\n')
            sys.exit(1)
        if status not in ('success', 'failed', 'pending'):
            sys.stderr.write(f'Row {line_num}: invalid status\n')
            sys.exit(1)
        try:
            ts = parse_timestamp(ts_str)
        except Exception:
            sys.stderr.write(f'Row {line_num}: invalid timestamp\n')
            sys.exit(1)
        if not is_finite_decimal(amt_str):
            sys.stderr.write(f'Row {line_num}: invalid amount\n')
            sys.exit(1)
        amount = decimal.Decimal(amt_str)
        # Keep latest per tx_id
        prev = records.get(tx_id)
        if prev is None or ts > prev['ts'] or (ts == prev['ts'] and line_num > prev['line']):
            records[tx_id] = {'ts': ts, 'amount': amount, 'status': status, 'line': line_num}
    # Compute aggregates
    total_valid_amount = decimal.Decimal('0')
    valid_count = 0
    for rec in records.values():
        if rec['status'] == 'success':
            total_valid_amount += rec['amount']
            valid_count += 1
        elif rec['status'] == 'failed':
            failed_count += 1
    result = {
        'total_valid_amount': float(total_valid_amount),
        'valid_count': valid_count,
        'failed_count': failed_count
    }
    json.dump(result, sys.stdout)
    sys.stdout.write('\n')
    sys.exit(0)

if __name__ == '__main__':
    main()
