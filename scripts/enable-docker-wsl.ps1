# VERSION: 2026-06-26-v2
# Admin PowerShell:
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\homework\coding6\scripts\enable-docker-wsl.ps1

$ErrorActionPreference = 'Continue'
Write-Host 'enable-docker-wsl.ps1 VERSION 2026-06-26-v2' -ForegroundColor Cyan

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host 'Please run PowerShell as Administrator.' -ForegroundColor Red
    exit 1
}

Write-Host '[1/5] Enable Windows optional features...' -ForegroundColor Yellow
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:HypervisorPlatform /all /norestart

Write-Host '[2/5] Update WSL (optional)...' -ForegroundColor Yellow
try {
    wsl --update --web-download
} catch {
    Write-Host '  wsl --update failed (often 403). If wsl --version works, ignore.' -ForegroundColor DarkYellow
}
wsl --version
wsl --set-default-version 2

Write-Host '[3/5] Check virtualization...' -ForegroundColor Yellow
Write-Host "  BIOS virtualization: $((Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled)"
Write-Host "  HyperVisorPresent: $((Get-ComputerInfo).HyperVisorPresent)"

Write-Host '[4/5] Try Neo4j via Docker (optional)...' -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $composeFile = Join-Path $PSScriptRoot '..\docker-compose.neo4j.yml'
    docker compose -f $composeFile up -d
    docker ps
} else {
    Write-Host '  docker not found. Start Docker Desktop after reboot.' -ForegroundColor DarkYellow
}

Write-Host '[5/5] Done. Reboot if HyperVisorPresent is False.' -ForegroundColor Green
