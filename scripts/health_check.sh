#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
quiet=0
[[ "${1:-}" != -q ]] || quiet=1
manage validate
expected="$(manage compose config --services)"
running="$(manage compose ps --status running --services)"
while IFS= read -r service; do
  [[ -z "$service" ]] && continue
  grep -Fxq "$service" <<<"$running" || { echo "ERROR: $service is not running"; exit 1; }
done <<<"$expected"
domain="$(manage get DOMAIN)"
ready=0
for ((attempt=1; attempt<=30; attempt++)); do
  if curl -fsS --connect-timeout 5 --max-time 10 "https://${domain}/healthz" | grep -q '"status":"ok"'; then
    ready=1; break
  fi
  sleep 2
done
[[ $ready -eq 1 ]] || { echo "ERROR: HTTPS health check failed (DNS/certificate/backend)"; exit 1; }
status="$(curl -sS --connect-timeout 5 --max-time 10 -o /dev/null -w '%{http_code}' "https://${domain}/admin")"
[[ "$status" == 401 ]] || { echo "ERROR: admin authentication check returned $status"; exit 1; }
profiles="$(manage get COMPOSE_PROFILES)"
if [[ ",$profiles," == *,wireguard,* ]]; then
  wg_domain="$(manage get WG_DOMAIN)"
  status="$(curl -sS --connect-timeout 5 --max-time 10 -o /dev/null -w '%{http_code}' "https://${wg_domain}/")"
  [[ "$status" == 401 ]] || { echo "ERROR: WireGuard UI protection returned $status"; exit 1; }
fi
manage check-protocols
if [[ $quiet -eq 0 ]]; then
  manage compose ps
  echo "Services, TLS and authentication checks passed. VPN client handshake still requires an external test."
fi
