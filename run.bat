@echo off
REM Double-click to start Vistara Vision. Pass a camera index or DroidCam URL as argument if needed.
cd /d "%~dp0"
".venv\Scripts\python.exe" main.py %*
pause
