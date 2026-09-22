$out = 'outputs/release/plex-server-bundle-20260831.tar.gz'
if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Force }
tar -czf $out -C outputs/release plex-server-bundle
Get-Item -LiteralPath $out | Select-Object Name,Length
(Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash
