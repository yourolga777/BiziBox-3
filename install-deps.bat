@echo off
echo Installing backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

echo Installing frontend dependencies...
cd /d "%~dp0frontend"
call npm install
if %errorlevel% neq 0 exit /b %errorlevel%

echo Done. All dependencies installed.
pause
