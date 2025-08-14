#!/usr/bin/env bash
set -euo pipefail
grep -q '^VLESS_UUID=' .env || echo 'VLESS_UUID=' >> .env
VAL=$(grep '^VLESS_UUID=' .env | cut -d= -f2)
if [[ -z "$VAL" ]]; then UUID=$(cat /proc/sys/kernel/random/uuid); sed -i "s|^VLESS_UUID=.*|VLESS_UUID=${UUID}|" .env; fi
docker build -q -t freenetvpn-admin ./admin >/dev/null || true
echo "Services prepared."
