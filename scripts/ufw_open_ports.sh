#!/usr/bin/env bash
set -euo pipefail
SERVICES="${1:-all}"
WG_PORT="${2:-51820}"
ufw allow 80/tcp
ufw allow 443/tcp
[[ "$SERVICES" == *"ipsec"* || "$SERVICES" == *"all"* ]] && { ufw allow 500/udp; ufw allow 4500/udp; }
[[ "$SERVICES" == *"l2tp"*  || "$SERVICES" == *"all"* ]] && ufw allow 1701/udp
[[ "$SERVICES" == *"wireguard"* || "$SERVICES" == *"all"* ]] && ufw allow ${WG_PORT}/udp
echo "UFW rules updated."
