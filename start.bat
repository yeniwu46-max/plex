@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"
set "ROOT=%CD%"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "VENV=%ROOT%\.venv"
set "BUNDLED_PYTHON=C:\Users\BX\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PYTHON="
set "NPM_CACHE=%ROOT%\.npm-cache"
set "CHECK_ONLY=0"
set "OPEN_BROWSER=1"
set "BACKEND_RUNNING=0"
set "FRONTEND_RUNNING=0"

if /I "%~1"=="--check" set "CHECK_ONLY=1"
if /I "%~1"=="--no-browser" set "OPEN_BROWSER=0"

echo ========================================
echo PLEX one-click startup
echo ========================================

if not exist "%BACKEND%\manage.py" goto :missing_backend
if not exist "%FRONTEND%\package.json" goto :missing_frontend
where py >nul 2>&1
if errorlevel 1 where python >nul 2>&1
if errorlevel 1 goto :missing_python
where node >nul 2>&1
if errorlevel 1 goto :missing_node
where npm >nul 2>&1
if errorlevel 1 goto :missing_npm

call :use_venv "%VENV%"

if not defined PYTHON (
    echo [1/6] Creating project virtual environment...
    py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
    if not errorlevel 1 (
        py -3.12 -m venv "%VENV%"
    ) else (
        if exist "%BUNDLED_PYTHON%" "%BUNDLED_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
        if not errorlevel 1 (
            "%BUNDLED_PYTHON%" -m venv "%VENV%"
        ) else (
            python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
            if errorlevel 1 (
                echo [ERROR] Python 3.12 is required to create a virtual environment.
                exit /b 1
            )
            python -m venv "%VENV%"
        )
    )
    if errorlevel 1 (
        echo [ERROR] Failed to create the Python virtual environment.
        exit /b 1
    )
    set "PYTHON=%VENV%\Scripts\python.exe"
) else (
    echo [1/6] Project virtual environment found: %VENV%
)

echo [2/6] Runtime versions
"%PYTHON%" --version
node --version
call npm --version
if errorlevel 1 exit /b 1

echo [3/6] Backend dependencies
"%PYTHON%" -m pip install -r "%BACKEND%\requirements.txt" --disable-pip-version-check >nul
if errorlevel 1 exit /b 1

echo [4/6] Frontend dependencies
if not exist "%FRONTEND%\node_modules\.package-lock.json" (
    pushd "%FRONTEND%"
    call npm ci --cache "%NPM_CACHE%"
    set "NPM_RESULT=%ERRORLEVEL%"
    popd
    if not "%NPM_RESULT%"=="0" exit /b 1
)

echo [5/6] Database migration and demo data
pushd "%BACKEND%"
"%PYTHON%" manage.py upgrade
if errorlevel 1 (
    "%PYTHON%" manage.py init
    if errorlevel 1 (
        popd
        exit /b 1
    )
)
"%PYTHON%" manage.py seed-demo
if errorlevel 1 (
    popd
    exit /b 1
)

echo [6/6] Health, database, and demo-account checks
"%PYTHON%" scripts\verify_clean_environment.py
if errorlevel 1 (
    popd
    exit /b 1
)
popd

if "%CHECK_ONLY%"=="1" (
    echo.
    echo All checks passed. No service was started.
    exit /b 0
)

call :check_backend
if errorlevel 1 exit /b 1
call :check_frontend
if errorlevel 1 exit /b 1

if "%BACKEND_RUNNING%"=="0" (
    echo Starting backend at http://127.0.0.1:5000
    start "PLEX Backend" /min /D "%BACKEND%" "%PYTHON%" run.py
) else (
    echo Backend already running at http://127.0.0.1:5000
)
if "%FRONTEND_RUNNING%"=="0" (
    echo Starting frontend at http://localhost:5173
    start "PLEX Frontend" /min /D "%FRONTEND%" cmd /k "npm run dev"
) else (
    echo Frontend already running at http://localhost:5173
)

if "%OPEN_BROWSER%"=="1" (
    start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://localhost:5173'"
)

echo PLEX startup commands launched.
echo Student: student001 / student123
echo Teacher: teacher001 / teacher123
echo Admin:   admin / admin123
exit /b 0

:use_venv
if not exist "%~1\Scripts\python.exe" exit /b 1
"%~1\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
set "VENV=%~1"
set "PYTHON=%~1\Scripts\python.exe"
exit /b 0

:check_backend
netstat -ano | findstr /R /C:":5000 .*LISTENING" >nul 2>&1
if errorlevel 1 exit /b 0
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5000/api/v1/health' -TimeoutSec 3; if ($r.StatusCode -eq 200 -and $r.Content -match 'code' -and $r.Content -match ': 0') { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Port 5000 is already in use, but it does not look like the PLEX Flask backend.
    exit /b 1
)
set "BACKEND_RUNNING=1"
exit /b 0

:check_frontend
netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul 2>&1
if errorlevel 1 exit /b 0
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://localhost:5173' -TimeoutSec 3; if ($r.StatusCode -eq 200 -and $r.Content -match '/@vite/client' -and $r.Content -match '<div id=') { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Port 5173 is already in use, but it does not look like the PLEX Vite frontend.
    exit /b 1
)
set "FRONTEND_RUNNING=1"
exit /b 0

:missing_backend
echo [ERROR] backend\manage.py was not found.
exit /b 1
:missing_frontend
echo [ERROR] frontend\package.json was not found.
exit /b 1
:missing_python
echo [ERROR] Python was not found.
exit /b 1
:missing_node
echo [ERROR] Node.js was not found.
exit /b 1
:missing_npm
echo [ERROR] npm was not found.
exit /b 1
