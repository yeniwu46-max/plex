#!/usr/bin/env bash
# Run on the ECS host after /opt/plex-a3 is uploaded.
set -euo pipefail

APP_DIR=/opt/plex-a3
NGINX_CONF=/etc/nginx/conf.d/pltek.cn.conf

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  dnf install -y docker
  systemctl enable --now docker
fi
if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
  dnf install -y docker-compose-plugin || true
fi
if ! command -v nginx >/dev/null 2>&1; then
  dnf install -y nginx
  systemctl enable --now nginx
fi

install -d -m 755 "$APP_DIR"
cp -f "$APP_DIR/nginx-pltek.cn.conf" "$NGINX_CONF"
nginx -t
systemctl reload nginx

cd "$APP_DIR"
if docker compose version >/dev/null 2>&1; then
  docker compose up -d --build
else
  docker-compose up -d --build
fi

echo "PLEX is up. Open http://106.15.77.40 and http://pltek.cn after DNS A records exist."
