@echo off
REM One-click launcher for FakeNews Detector Pro
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv venv
  venv\Scripts\python.exe -m pip install --upgrade pip
  venv\Scripts\python.exe -m pip install -r requirements.txt
)
echo Starting FakeNews Detector Pro at http://127.0.0.1:5000
start "" http://127.0.0.1:5000
venv\Scripts\python.exe app.py
