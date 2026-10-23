@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py %*
    pause
    exit /b
)
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 main.py %*
) else (
    python main.py %*
)
pause
