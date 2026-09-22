# PLEX A3 server deployment

This directory is copied to `/opt/plex-a3` on the target host.

- `backend/`: Flask API source and runtime data
- `frontend-dist/`: production Vue build
- `docker-compose.yml`: isolated backend container
- `nginx-pltek.cn.conf`: Nginx static frontend and `/api` reverse proxy

The deployment keeps existing services untouched. The backend binds only to
`127.0.0.1:5100`; public traffic is handled by Nginx.
