@echo off
title go_fast - Rocket Speed Accelerator
cls

echo ========================================================
echo        go_fast 🚀 Universal Rocket Speed Accelerator
echo ========================================================
echo.
echo Checking Python environment...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in your PATH.
    echo Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

echo Starting High-Speed Accelerator and Dashboard...
echo Dashboard will automatically open in your browser...
echo.
python run.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application stopped with an error.
    pause
)
