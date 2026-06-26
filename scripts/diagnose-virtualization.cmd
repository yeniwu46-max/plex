@echo off
REM Run as Administrator. Writes report to scripts\diagnostic-report.txt
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Run this file as Administrator.
    pause
    exit /b 1
)

set LOG=%~dp0diagnostic-report.txt
echo Diagnostic report %DATE% %TIME% > "%LOG%"
echo. >> "%LOG%"

echo === Windows edition === >> "%LOG%"
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v EditionID >> "%LOG%"

echo. >> "%LOG%"
echo === DISM optional features === >> "%LOG%"
dism /online /get-featureinfo /featurename:VirtualMachinePlatform >> "%LOG%"
dism /online /get-featureinfo /featurename:Microsoft-Windows-Subsystem-Linux >> "%LOG%"
dism /online /get-featureinfo /featurename:HypervisorPlatform >> "%LOG%"

echo. >> "%LOG%"
echo === bcdedit hypervisor === >> "%LOG%"
bcdedit /enum {current} >> "%LOG%"

echo. >> "%LOG%"
echo === WSL === >> "%LOG%"
wsl --version >> "%LOG%"
wsl --status >> "%LOG%"
wsl -l -v >> "%LOG%"

echo. >> "%LOG%"
echo === Services === >> "%LOG%"
sc query vmcompute >> "%LOG%"
sc query LxssManager >> "%LOG%"
sc query HvHost >> "%LOG%"

echo Report saved: %LOG%
type "%LOG%"
pause
