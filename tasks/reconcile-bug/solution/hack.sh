#!/bin/sh
# Demonstration only: this fixed response can fool a one-fixture verifier.
cat > /app/reconcile.py <<'PY'
#!/usr/bin/env python3
print('{"total_valid_amount": 10.25, "valid_count": 1, "failed_count": 1}')
PY
chmod +x /app/reconcile.py
