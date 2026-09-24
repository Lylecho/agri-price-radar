@echo off
REM =====================================================================
REM AgriPriceRadar - collector scheduler launcher (W1/W2.2)
REM Runs APScheduler: collect at 08/14/20, precompute at 21 (Asia/Shanghai)
REM DB credentials are loaded from python\.env by config/db.py
REM Usage: double-click, or call from Task Scheduler / Startup folder
REM =====================================================================
chcp 65001 >nul
cd /d "%~dp0..\.."

echo [AgriPriceRadar] workdir: %CD%
echo [AgriPriceRadar] starting scheduler (Ctrl+C to stop) ...
echo.

python python\scheduler\run.py
set EXITCODE=%ERRORLEVEL%
echo.
echo [AgriPriceRadar] scheduler exited with code %EXITCODE%
exit /b %EXITCODE%