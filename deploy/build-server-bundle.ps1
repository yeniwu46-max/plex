$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root "outputs\release\plex-server-bundle"
$backendSrc = Join-Path $root "backend"
$frontendSrc = Join-Path $root "frontend"
$deploySrc = Join-Path $root "deploy\plex-server"

if (Test-Path -LiteralPath $bundle) {
  Remove-Item -LiteralPath $bundle -Recurse -Force
}
New-Item -ItemType Directory -Path $bundle, "$bundle\backend", "$bundle\frontend-dist" | Out-Null

Copy-Item -LiteralPath @(
  "$deploySrc\Dockerfile",
  "$deploySrc\docker-compose.yml",
  "$deploySrc\nginx-pltek.cn.conf",
  "$deploySrc\README.md",
  "$deploySrc\setup-host.sh"
) -Destination $bundle

robocopy $backendSrc "$bundle\backend" /E /NFL /NDL /NJH /NJS /nc /ns /np `
  /XD .venv .venv-crewai __pycache__ .pytest_cache .cache output outputs instance media `
  /XF *.log *.pyc .env .env.spark.local | Out-Null

New-Item -ItemType Directory -Path "$bundle\backend\instance", "$bundle\backend\media" | Out-Null
$db = Join-Path $backendSrc "instance\learning_system.db"
if (Test-Path -LiteralPath $db) {
  Copy-Item -LiteralPath $db -Destination "$bundle\backend\instance\learning_system.db" -Force
}

$envOut = Join-Path $bundle "backend\.env"
python -c @"
from pathlib import Path
src = Path(r'$backendSrc') / '.env'
spark = Path(r'$backendSrc') / '.env.spark.local'
lines = []
replacements = {
    'FLASK_ENV': 'production',
    'FLASK_DEBUG': '0',
    'DATABASE_URL': 'sqlite:///instance/learning_system.db',
    'FRONTEND_BASE_URL': 'https://pltek.cn',
    'CORS_ORIGINS': 'https://pltek.cn,https://www.pltek.cn,http://pltek.cn,http://www.pltek.cn,http://106.15.77.40',
}
if src.exists():
    for raw in src.read_text(encoding='utf-8').splitlines():
        if not raw.strip() or raw.lstrip().startswith('#') or '=' not in raw:
            lines.append(raw)
            continue
        key = raw.split('=', 1)[0]
        if key in replacements:
            lines.append(f'{key}={replacements.pop(key)}')
        else:
            lines.append(raw)
    for key, value in replacements.items():
        lines.append(f'{key}={value}')
Path(r'$envOut').write_text('\n'.join(lines) + '\n', encoding='utf-8')
if spark.exists():
    (Path(r'$bundle') / 'backend' / '.env.spark.local').write_bytes(spark.read_bytes())
"@

Push-Location $frontendSrc
$env:VITE_API_BASE_URL = "/api"
npx --yes vite build
if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
Pop-Location
Copy-Item -Path (Join-Path $frontendSrc "dist\*") -Destination "$bundle\frontend-dist" -Recurse -Force

$tar = Join-Path $root "outputs\release\plex-server-bundle.tar.gz"
if (Test-Path -LiteralPath $tar) { Remove-Item -LiteralPath $tar -Force }
tar -czf $tar -C (Join-Path $root "outputs\release") plex-server-bundle
Get-Item -LiteralPath $tar | Select-Object FullName, Length
Write-Output "bundle ready"
