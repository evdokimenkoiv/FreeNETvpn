#!/usr/bin/env bash
set -euo pipefail
NEW_UUID=$(cat /proc/sys/kernel/random/uuid)
NEW_PATH="/assets-$(tr -dc a-z </dev/urandom | head -c 6)"
sed -i "s|^VLESS_UUID=.*|VLESS_UUID=${NEW_UUID}|" .env
sed -i "s|^VLESS_WS_PATH=.*|VLESS_WS_PATH=${NEW_PATH}|" .env
docker compose up -d xray caddy
echo "Rotated VLESS to UUID=${NEW_UUID}, path=${NEW_PATH}"
