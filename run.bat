@echo off
setlocal
cd /d "%~dp0"
for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d" 2>nul
set PYTHONDONTWRITEBYTECODE=1
.venv\Scripts\python.exe main.py %1
