@echo off
chcp 65001 >nul
title BiziBox Dev Server

echo ========================================
echo       BiziBox — Dev Server
echo ========================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Install Python 3.12+ and try again.
    pause
    exit /b 1
)

python --version 2>&1 | findstr "3." >nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python version check failed.
    pause
    exit /b 1
)

where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js not found. Install Node.js 18+ and try again.
    pause
    exit /b 1
)

echo [OK] Python ^& Node.js found
echo.

echo Starting backend (uvicorn)...
start "BiziBox-Backend" cmd /c "cd /d "%~dp0" && uvicorn app.main:app --reload --port 7910"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start backend.
    pause
    exit /b 1
)

timeout /t 3 /nobreak >nul

echo Starting frontend (vite)...
start "BiziBox-Frontend" cmd /c "cd /d "%~dp0..\frontend" && npm run dev"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start frontend.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Backend:  http://localhost:7910
echo  Frontend: http://localhost:5173
echo  API docs: http://localhost:7910/docs
echo ========================================
echo.
echo Close both server windows or press Ctrl+C to stop.
echo.

:wait
timeout /t 10 /nobreak >nul
goto wait
