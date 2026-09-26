@echo off
setlocal
cd /d "%~dp0"

if defined PYTHON_BIN goto :have_python

set "PYTHON_BIN=py"
set "PYTHON_ARGS=-3.14"
py -3.14 -c "print(1)" >nul 2>nul
if not errorlevel 1 goto :have_python

set "PYTHON_BIN=python"
set "PYTHON_ARGS="
where python >nul 2>nul
if not errorlevel 1 goto :have_python

echo Error: no Python interpreter found in PATH.
echo Tip: install Python 3.14 from https://www.python.org/downloads/ (check "Add to PATH"),
echo or point PYTHON_BIN at another interpreter, e.g.:
echo   set PYTHON_BIN=C:\Python314\python.exe
echo   setup.bat
exit /b 1

:have_python
"%PYTHON_BIN%" %PYTHON_ARGS% -m venv .venv
if errorlevel 1 (
  echo Setup failed during: virtualenv creation
  exit /b 1
)

call .venv\Scripts\activate.bat

set "pip_args="
if defined PIP_INDEX_URL set "pip_args=%pip_args% --index-url %PIP_INDEX_URL%"
if defined PIP_EXTRA_INDEX_URL set "pip_args=%pip_args% --extra-index-url %PIP_EXTRA_INDEX_URL%"

if not defined UPGRADE_PIP set "UPGRADE_PIP=0"

if "%UPGRADE_PIP%"=="1" (
  python -m pip install --upgrade pip %pip_args%
  if errorlevel 1 (
    echo:
    echo Setup failed during: pip upgrade
    echo Likely cause: network/DNS access to PyPI is unavailable.
    echo Quick checks:
    echo   nslookup files.pythonhosted.org
    echo   nslookup pypi.org
    echo If you use a mirror, run:
    echo   set PIP_INDEX_URL=https://^<your-mirror^>/simple
    echo   setup.bat
    call deactivate >nul 2>nul
    exit /b 1
  )
) else (
  echo Skipping pip self-upgrade - set UPGRADE_PIP=1 to enable.
)

pip install -r requirements.txt %pip_args%
if errorlevel 1 (
  echo.
  echo Setup failed during: dependency install
  echo Likely cause: network/DNS access to PyPI is unavailable.
  echo Quick checks:
  echo   nslookup files.pythonhosted.org
  echo   nslookup pypi.org
  echo If you use a mirror, run:
  echo   set PIP_INDEX_URL=https://^<your-mirror^>/simple
  echo   setup.bat
  call deactivate >nul 2>nul
  exit /b 1
)

call deactivate >nul 2>nul
echo Setup complete.

pause
