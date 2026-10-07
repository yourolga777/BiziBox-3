@echo off
echo Starting BiziBox backend...
cd /d "%~dp0backend"
python -m uvicorn app.main:app --reload --port 7910
if %errorlevel% neq 0 (
  echo Failed to start backend.
  pause
  exit /b %errorlevel%
)
