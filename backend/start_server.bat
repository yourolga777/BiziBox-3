@echo off
cd /d "%~dp0"
call .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 7910 > ..\server_out.txt 2>&1
