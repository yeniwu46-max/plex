@echo off
REM VERSION: 2026-06-26-v3 - fix Virtual Machine Platform for Docker/WSL2
REM Right-click -> Run as administrator
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo fix-virtualization.cmd VERSION 2026-06-26-v3
echo.

echo [1/6] Enable Windows optional features (DISM)...
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:HypervisorPlatform /all /norestart

echo [2/6] Set hypervisor launch type to Auto (bcdedit)...
bcdedit /set hypervisorlaunchtype auto

echo [3/6] Complete WSL2 setup (no Linux distro)...
wsl --install --no-distribution
wsl --set-default-version 2

echo [4/6] If step 3 failed, try inbox WSL install...
wsl --install --no-distribution --inbox

echo [5/6] Feature state after changes:
dism.exe /online /get-featureinfo /featurename:VirtualMachinePlatform | findstr /i "State"
dism.exe /online /get-featureinfo /featurename:Microsoft-Windows-Subsystem-Linux | findstr /i "State"

echo [6/6] IMPORTANT
echo   1. REBOOT your PC now (required).
echo   2. After reboot, open optionalfeatures and confirm these are checked:
echo      - Virtual Machine Platform (虚拟机平台)
echo      - Windows Subsystem for Linux
echo   3. If Docker still fails: Settings - Privacy - Windows Security -
echo      Device Security - Core isolation - turn OFF Memory integrity, reboot again.
echo   4. Then open Docker Desktop and wait for Engine running.
echo.
pause
