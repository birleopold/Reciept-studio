@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (
  pause
  exit /b 1
)
start "" http://127.0.0.1:8765
python app.py --port 8765
pause
