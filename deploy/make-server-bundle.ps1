$stage = (Get-ChildItem 'outputs/release/PLEX-A3-complete-runnable-20260731' -Directory | Select-Object -First 1).FullName
$bundle = Join-Path (Resolve-Path 'outputs/release').Path 'plex-server-bundle'
if (Test-Path -LiteralPath $bundle) { Remove-Item -LiteralPath $bundle -Recurse -Force }
New-Item -ItemType Directory -Path $bundle, "$bundle\backend", "$bundle\backend\instance", "$bundle\frontend-dist" | Out-Null
Copy-Item -LiteralPath 'deploy/plex-server/Dockerfile','deploy/plex-server/docker-compose.yml','deploy/plex-server/nginx-pltek.cn.conf','deploy/plex-server/README.md' -Destination $bundle
Copy-Item -Path (Join-Path $stage 'source/backend/*') -Destination "$bundle\backend" -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath "$bundle\backend\instance") { Remove-Item -LiteralPath "$bundle\backend\instance" -Recurse -Force }
New-Item -ItemType Directory -Path "$bundle\backend\instance" | Out-Null
Copy-Item -LiteralPath (Join-Path $stage 'data/database/learning_system.db') -Destination "$bundle\backend\instance\learning_system.db" -Force
Copy-Item -LiteralPath (Join-Path $stage 'config-samples/backend.env.production-ready') -Destination "$bundle\backend\.env" -Force
if (Test-Path (Join-Path $stage 'config-samples/api-keys.spark.local')) { Copy-Item -LiteralPath (Join-Path $stage 'config-samples/api-keys.spark.local') -Destination "$bundle\backend\.env.spark.local" -Force }
Copy-Item -Path (Join-Path $stage 'runtime/frontend-dist/*') -Destination "$bundle\frontend-dist" -Recurse -Force
Get-ChildItem -LiteralPath $bundle -Force | Select-Object Name,Length,Mode
Write-Output ((Get-ChildItem -LiteralPath $bundle -Recurse -File | Measure-Object Length -Sum).Sum)
