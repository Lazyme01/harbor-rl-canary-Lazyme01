#!/bin/sh
mkdir -p /logs/verifier
if python3 /tests/test_state.py; then
  printf '1.0\n' > /logs/verifier/reward.txt
else
  printf '0.0\n' > /logs/verifier/reward.txt
fi
