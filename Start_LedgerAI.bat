@echo off
set "PROJECT_DIR=%~dp0"
title LedgerAI Launcher

echo ======================================================
echo           LEDGER AI — Starting Application
echo ======================================================
echo.

:: Start Backend
echo [1/3] Starting Backend (FastAPI)...
start "LedgerAI Backend" cmd /c "cd /d %PROJECT_DIR%\backend && python main.py"

:: Start Frontend
echo [2/3] Starting Frontend (Vite)...
start "LedgerAI Frontend" cmd /c "cd /d %PROJECT_DIR%\frontend && npm run dev"

:: Wait for servers to initialize
echo [3/3] Waiting for servers to start...
timeout /t 5 /nobreak > nul

:: Open Browser
echo Opening Browser...
start http://localhost:5173

echo.
echo ======================================================
echo    Application is running! 
echo    Keep the command windows open while using the app.
echo ======================================================
echo.
pause
