@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"
if not defined FLASK_ENV set "FLASK_ENV=development"
if not defined SERVER_PORT set "SERVER_PORT=5100"
set "NO_PROXY=127.0.0.1,localhost,::1,api.deepseek.com,spark-api-open.xf-yun.com,xingchen-api.xf-yun.com"
set "no_proxy=127.0.0.1,localhost,::1,api.deepseek.com,spark-api-open.xf-yun.com,xingchen-api.xf-yun.com"

if defined PLEX_PYTHON (
    set "PYTHON=%PLEX_PYTHON%"
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PYTHON=%~dp0..\.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo Starting PLEX backend on port %SERVER_PORT% ...
"%PYTHON%" run.py
if errorlevel 1 (
    echo.
    echo [ERROR] Backend failed to start. Check messages above.
    pause
)
exit /b %ERRORLEVEL%
