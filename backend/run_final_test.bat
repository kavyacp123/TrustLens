@echo off
REM Final test to verify all metrics and agents working

cd /d c:\Users\Kavya\OneDrive\Desktop\trustlens\TrustLens\backend

echo ================================================================================
echo   FINAL END-TO-END TEST - ALL METRICS & AGENTS
echo ================================================================================
echo.

python test_full_flow_debug.py

echo.
echo Test complete! Check output for:
echo   - Stage 1: Total LoC should be 151
echo   - Stage 2: Metrics should flow to Routing Policy
echo   - Code Quality Agent: Should now show SUCCESS
echo.

pause
