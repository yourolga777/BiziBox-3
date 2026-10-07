@echo off

echo ========================================
echo     BiziBox - Dev Server Launcher
echo ========================================
echo.

REM === Kill old processes ===
echo [1/3] Cleaning up old processes...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":7910"') do (
    if not "%%a"=="" taskkill /F /PID %%a >nul 2>&1 && echo   Killed process on port 7910
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /C:":5173"') do (
    if not "%%a"=="" taskkill /F /PID %%a >nul 2>&1 && echo   Killed process on port 5173
)

timeout /t 2 /nobreak >nul

REM === Start Backend ===
echo [2/3] Starting backend (port 7910)...

start "BiziBox Backend" cmd /k "cd /d %~dp0..\backend && set PYTHONPATH=%~dp0..\backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 7910 --reload"

timeout /t 4 /nobreak >nul

REM === Start Frontend ===
echo [3/3] Starting frontend (port 5173)...

start "BiziBox Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"

REM === Wait for frontend to be ready ===
echo [3/3] Waiting for frontend...

for /l %%i in (1,1,15) do (
    >nul 2>&1 curl -s --connect-timeout 2 http://127.0.0.1:5173 && goto :OPEN
    >nul 2>&1 powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }" && goto :OPEN
    timeout /t 1 /nobreak >nul
)

:OPEN

echo.
echo ========================================
echo   Backend:  http://localhost:7910/docs
echo   Frontend: http://localhost:5173
echo ========================================
echo.

REM === Open browser, disable extensions to avoid conflicts ===
where chrome >nul 2>&1
if not errorlevel 1 (
    start "" chrome --new-window --disable-extensions "http://localhost:5173"
) else (
    start "" http://localhost:5173
)

echo.
echo Close the server windows to stop.
pause
