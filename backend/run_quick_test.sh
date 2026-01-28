#!/bin/bash
# Final test to verify metrics fix

cd "$(dirname "$0")"

echo "🚀 Running Full Flow Test - METRICS FIX"
echo ""

python3 test_full_flow_debug.py 2>&1 | grep -A 50 "STAGE 2"
