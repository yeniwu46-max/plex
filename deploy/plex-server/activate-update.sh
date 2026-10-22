#!/usr/bin/env bash
# Existing SQLite + systemd host only. Run prepare-update.py and preflight first.
set -euo pipefail
root=/opt/plex-a3
name=${1:?release name required}
[[ "$name" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
release="$root/releases/$name"
rollback="$root/backend.rollback-$name"
[[ -f "$release/preflight.ok" && -d "$release/backend/app" && ! -e "$rollback" ]] || exit 3
cp -a "$root/frontend-dist" "$root/frontend-dist.rollback-$name"
systemctl stop plex-backend
switched=0
recover() {
  code=$?
  if (( code != 0 )); then
    if (( switched == 1 )); then
      mv "$root/backend" "$release/failed-backend"
      mv "$rollback" "$root/backend"
      cp "$root/frontend-dist.rollback-$name/index.html" "$root/frontend-dist/index.html"
    fi
    systemctl start plex-backend || true
    echo "Activation failed; old code restored. Additive schema retained; inspect the private backup before any database rollback." >&2
  fi
  exit "$code"
}
trap recover EXIT
# Service is stopped, so backup and row-count checks see a consistent database.
ROOT="$root" RELEASE="$release" "$root/venv/bin/python" - <<'PY'
import os, sqlite3
from pathlib import Path
root, release = Path(os.environ['ROOT']), Path(os.environ['RELEASE'])
source = sqlite3.connect(f'file:{root / "backend/instance/learning_system.db"}?mode=ro',uri=True)
target = sqlite3.connect(release / 'database-before.db')
source.backup(target); source.close(); target.close()
(release / 'database-before.db').chmod(0o600)
PY
cd "$release/backend"
"$root/venv/bin/python" "$release/deploy/plex-server/strict-migrate.py" "$release/backend"
mv "$root/backend" "$rollback"
if ! mv "$release/backend" "$root/backend"; then
  mv "$rollback" "$root/backend"
  exit 4
fi
switched=1
systemctl start plex-backend
ready=0
for i in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:5100/api/v1/health >/dev/null; then ready=1; break; fi
  sleep 1
done
[[ "$ready" == 1 ]] || exit 5
# Preserve old hashed assets for already-open clients; publish HTML last.
cp -a "$release/frontend-dist/." "$root/frontend-dist.next-$name"
find "$root/frontend-dist.next-$name" -type d -exec chmod 755 {} +
find "$root/frontend-dist.next-$name" -type f -exec chmod 644 {} +
cp -a "$root/frontend-dist.next-$name/assets/." "$root/frontend-dist/assets/"
find "$root/frontend-dist.next-$name" -mindepth 1 -maxdepth 1 ! -name assets ! -name index.html -exec cp -a {} "$root/frontend-dist/" \;
cp "$root/frontend-dist.next-$name/index.html" "$root/frontend-dist/index.html.next"
mv "$root/frontend-dist/index.html.next" "$root/frontend-dist/index.html"
printf '%s\n' "$name" > "$root/current-release"
echo "Activated $name"
