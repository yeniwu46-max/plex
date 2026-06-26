@echo off
REM VERSION: 2026-06-26-v2 - no PowerShell parsing, DISM only
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo enable-docker-wsl.cmd VERSION 2026-06-26-v2
echo [1/3] Enable WSL and Virtual Machine Platform...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:HypervisorPlatform /all /norestart

echo [2/3] Update WSL (optional, skip if 403)...
wsl --update --web-download
if %errorLevel% neq 0 (
    echo WSL update failed - often 403 from Microsoft CDN. If wsl --version works, you can ignore this.
    wsl --version
)
wsl --set-default-version 2

echo [3/3] Done. Reboot PC, then open Docker Desktop.
pause
