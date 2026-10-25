@echo off
setlocal
title booster - Local Plugin
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    py -3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Install Python 3.10+ and add it to PATH.
        pause
        exit /b 1
    )
    py -3 setup_plugin.py %*
) else (
    python setup_plugin.py %*
)
if errorlevel 1 (
    echo [ERROR] Plugin setup or launch failed. See the message above.
    pause
    exit /b 1
)
