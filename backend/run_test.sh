#!/bin/bash
# Run the full flow test

cd "$(dirname "$0")"
echo "📍 Current Directory: $(pwd)"
echo ""

# Check Python version
python3 --version

echo ""
echo "🚀 Starting Full Flow Test..."
echo ""

python3 test_full_flow_debug.py
