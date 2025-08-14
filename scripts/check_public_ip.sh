#!/usr/bin/env bash
set -euo pipefail
DOMAIN="${1:-}"
PUB4=$(curl -4 -fsS https://api.ipify.org || true)
PUB6=$(curl -6 -fsS https://api64.ipify.org || true)
IPS=$(getent ahosts "$DOMAIN" | awk '{print $1}' | sort -u || true)
[[ -z "$DOMAIN" || -z "$IPS" ]] && exit 1
for ip in $IPS; do [[ "$ip" == "$PUB4" || "$ip" == "$PUB6" ]] && exit 0; done
exit 1
