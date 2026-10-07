@echo off
echo Starting BiziBox frontend...
cd /d "%~dp0frontend"
call npm run dev
if %errorlevel% neq 0 (
  echo Failed to start frontend.
  pause
  exit /b %errorlevel%
)
