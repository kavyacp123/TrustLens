#!/bin/bash
# Quick test runner with focus on metrics logging

cd "$(dirname "$0")"

echo "🚀 Running Full Flow Test with Detailed Metrics Logging..."
echo ""

python3 test_full_flow_debug.py 2>&1 | tee test_output.log

echo ""
echo "✅ Test complete. Output saved to test_output.log"
