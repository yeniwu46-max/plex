@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo ========================================
echo Start MySQL service (admin)
echo ========================================

net start MySQL267 >nul 2>&1
if errorlevel 1 (
    echo MySQL267 failed, trying MySQL93...
    net start MySQL93
    if errorlevel 1 (
        echo [ERROR] Could not start MySQL267 or MySQL93.
        pause
        exit /b 1
    )
)

echo Waiting for port 3306...
for /L %%I in (1,1,30) do (
    netstat -ano | findstr /R /C:":3306 .*LISTENING" >nul 2>&1
    if not errorlevel 1 (
        echo MySQL is listening on port 3306.
        exit /b 0
    )
    timeout /t 1 /nobreak >nul
)

echo [ERROR] MySQL service started but port 3306 is not listening.
pause
exit /b 1
