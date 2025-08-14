#!/usr/bin/env bash
set -euo pipefail
DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2)
UUID=$(grep '^VLESS_UUID=' .env | cut -d= -f2)
PATHP=$(grep '^VLESS_WS_PATH=' .env | cut -d= -f2)
PORT=443
URI="vless://${UUID}@${DOMAIN}:${PORT}?encryption=none&security=tls&sni=${DOMAIN}&alpn=h2,http/1.1&type=ws&host=${DOMAIN}&path=${PATHP}#FreeNETvpn"
mkdir -p services/xray/clients
echo "$URI" | tee "services/xray/clients/${DOMAIN}-${UUID}.txt"
echo "Saved: services/xray/clients/${DOMAIN}-${UUID}.txt"
