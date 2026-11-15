#!/bin/sh
mkdir -p /logs/verifier
if score="$(python3 /tests/test_state.py)"; then
  case "$score" in
    0.00|0.20|0.30|0.50|0.70|0.80|1.00)
      printf '%s\n' "$score" > /logs/verifier/reward.txt
      exit 0
      ;;
  esac
fi
printf '0.00\n' > /logs/verifier/reward.txt
