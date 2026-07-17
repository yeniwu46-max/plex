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
set "BACKEND_PORT=5100"
set "FRONTEND_PORT=5180"
set "NPM_CACHE=%ROOT%\.npm-cache"
set "CHECK_ONLY=0"
set "OPEN_BROWSER=1"
set "BACKEND_RUNNING=0"
set "FRONTEND_RUNNING=0"
set "WAIT_SECONDS=30"
set "HELP_ONLY=0"

call :parse_args %*
if errorlevel 1 exit /b 1
if "%HELP_ONLY%"=="1" exit /b 0

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
    echo Starting backend at http://127.0.0.1:%BACKEND_PORT%
    start "PLEX Backend" /min /D "%BACKEND%" cmd /c "set SERVER_PORT=%BACKEND_PORT%&& \"%PYTHON%\" run.py"
) else (
    echo Backend already running at http://127.0.0.1:%BACKEND_PORT%
)
if "%FRONTEND_RUNNING%"=="0" (
    echo Starting frontend at http://localhost:%FRONTEND_PORT%
    start "PLEX Frontend" /min /D "%FRONTEND%" cmd /k "npm run dev"
) else (
    echo Frontend already running at http://localhost:%FRONTEND_PORT%
)

echo Waiting for services to become ready...
call :wait_backend
if errorlevel 1 exit /b 1
call :wait_frontend
if errorlevel 1 exit /b 1

if "%OPEN_BROWSER%"=="1" (
    start "" "http://localhost:%FRONTEND_PORT%"
)

echo PLEX is ready.
echo Student: student001 / student123
echo Teacher: teacher001 / teacher123
echo Admin:   admin / admin123
exit /b 0

:parse_args
if "%~1"=="" exit /b 0
if /I "%~1"=="--check" (
    set "CHECK_ONLY=1"
    shift
    goto :parse_args
)
if /I "%~1"=="--no-browser" (
    set "OPEN_BROWSER=0"
    shift
    goto :parse_args
)
if /I "%~1"=="--help" (
    call :show_help
    set "HELP_ONLY=1"
    exit /b 0
)
if /I "%~1"=="/?" (
    call :show_help
    set "HELP_ONLY=1"
    exit /b 0
)
echo [ERROR] Unknown option: %~1
echo.
call :show_help
exit /b 1

:show_help
echo Usage: start.bat [--check] [--no-browser]
echo.
echo   --check       Run environment, database, health, and demo-account checks only.
echo   --no-browser  Start or reuse services without opening the browser.
exit /b 0

:use_venv
if not exist "%~1\Scripts\python.exe" exit /b 1
"%~1\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
set "VENV=%~1"
set "PYTHON=%~1\Scripts\python.exe"
exit /b 0

:check_backend
netstat -ano | findstr /R /C:":%BACKEND_PORT% .*LISTENING" >nul 2>&1
if errorlevel 1 exit /b 0
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:%BACKEND_PORT%/api/v1/health' -TimeoutSec 3; $json = $r.Content | ConvertFrom-Json; if ($r.StatusCode -eq 200 -and $json.code -eq 0) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Port %BACKEND_PORT% is already in use, but it does not look like the PLEX Flask backend.
    exit /b 1
)
set "BACKEND_RUNNING=1"
exit /b 0

:check_frontend
netstat -ano | findstr /R /C:":%FRONTEND_PORT% .*LISTENING" >nul 2>&1
if errorlevel 1 exit /b 0
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://localhost:%FRONTEND_PORT%' -TimeoutSec 3; if ($r.StatusCode -eq 200 -and $r.Content -match '/@vite/client' -and $r.Content -match '<div id=') { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Port %FRONTEND_PORT% is already in use, but it does not look like the PLEX Vite frontend.
    exit /b 1
)
set "FRONTEND_RUNNING=1"
exit /b 0

:wait_backend
for /L %%I in (1,1,%WAIT_SECONDS%) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:%BACKEND_PORT%/api/v1/health' -TimeoutSec 2; $json = $r.Content | ConvertFrom-Json; if ($r.StatusCode -eq 200 -and $json.code -eq 0) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        echo Backend health check passed.
        exit /b 0
    )
    timeout /t 1 /nobreak >nul
)
echo [ERROR] Backend did not become healthy within %WAIT_SECONDS% seconds.
echo Check the PLEX Backend window for the Flask error.
exit /b 1

:wait_frontend
for /L %%I in (1,1,%WAIT_SECONDS%) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing 'http://localhost:%FRONTEND_PORT%' -TimeoutSec 2; if ($r.StatusCode -eq 200 -and $r.Content -match '/@vite/client') { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        echo Frontend health check passed.
        exit /b 0
    )
    timeout /t 1 /nobreak >nul
)
echo [ERROR] Frontend did not become ready within %WAIT_SECONDS% seconds.
echo Check the PLEX Frontend window for the Vite error.
exit /b 1

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
