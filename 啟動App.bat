@echo off
cd /d "%~dp0"
where py >NUL 2>&1 && (py -3 tracker\app.py) || (python tracker\app.py)
if errorlevel 1 pause
