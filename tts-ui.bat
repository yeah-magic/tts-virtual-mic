@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
for %%p in ("pythonw.exe" "python.exe" "py.exe") do (
  where %%p >nul 2>&1 && set "PY=%%~p" && goto :found
)
echo Python not found. Install Python 3.9+ first: https://www.python.org/downloads/
pause
exit /b 1
:found
start "" "%PY%" "speak-mic-ui.py"
exit /b 0
