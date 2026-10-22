# PLEX A3 server deployment

This directory is copied to `/opt/plex-a3` on the target host.

- `backend/`: Flask API source and runtime data
- `frontend-dist/`: production Vue build
- `docker-compose.yml`: isolated backend container
- `nginx-pltek.cn.conf`: Nginx static frontend and `/api` reverse proxy

The deployment keeps existing services untouched. The backend binds only to
`127.0.0.1:5100`; public traffic is handled by Nginx.

## Updating the existing systemd / SQLite host

Use the code-only `../build-update-bundle.py`, `prepare-update.py`,
`strict-migrate.py` and `activate-update.sh` workflow described in
[the release handoff](../../docs/2026-10-22-release-and-handoff.md).
It preserves the server's private environment, database and media, performs
migrations on a backup first and keeps rollback copies. Do not use the older
full bootstrap bundle to overwrite a live host with local databases.

The activation script requires a release-local `preflight.ok` marker, created
only after migration and actual container execution checks pass. The current
host exposes Podman through Docker-compatible CLI commands; the sandbox image
must be built explicitly from `../code-sandbox/Dockerfile` before grading.
Never remove runtime directories referenced by symlinks from the active backend.
