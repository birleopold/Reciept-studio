@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" app.py --open-browser
if errorlevel 1 goto failed
exit /b 0

:failed
echo Receipt Studio could not start. Check that Python is installed and available on PATH.
pause
exit /b 1
