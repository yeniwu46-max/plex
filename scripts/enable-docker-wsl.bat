@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo Running enable-docker-wsl.ps1 ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0enable-docker-wsl.ps1"
echo.
pause
