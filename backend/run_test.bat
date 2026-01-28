@echo off
REM Run the full flow test on Windows

cd /d "%~dp0"
echo 📍 Current Directory: %cd%
echo.

REM Check Python version
python --version

echo.
echo 🚀 Starting Full Flow Test...
echo.

python test_full_flow_debug.py
pause
