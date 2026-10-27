#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
quiet=0
diagnostic_flags=()
for argument in "$@"; do
  case "$argument" in
    -q) quiet=1 ;;
    --no-firewall) diagnostic_flags+=(--no-firewall) ;;
    *) echo 'Usage: bash scripts/health_check.sh [-q] [--no-firewall]' >&2; exit 1 ;;
  esac
done
diagnose() {
  python3 tools/diagnostics.py "$@" "${diagnostic_flags[@]}" || true
}
manage validate
expected="$(manage compose config --services)"
running="$(manage compose ps --status running --services)"
while IFS= read -r service; do
  [[ -z "$service" ]] && continue
  grep -Fxq "$service" <<<"$running" || { echo "ERROR [SERVICE_STOPPED]: $service is not running" >&2; diagnose stage --phase startup; exit 1; }
done <<<"$expected"
domain="$(manage get DOMAIN)"
ready=0
probe="$(mktemp -d)"
trap 'rm -rf -- "$probe"' EXIT
curl_code=0
status=000
for ((attempt=1; attempt<=30; attempt++)); do
  curl_code=0
  status="$(curl -sS --connect-timeout 5 --max-time 10 -o "$probe/body" -w '%{http_code}' "https://${domain}/healthz" 2>"$probe/error")" || curl_code=$?
  if [[ $curl_code -eq 0 && "$status" == 200 ]] && grep -q '"status":"ok"' "$probe/body"; then
    ready=1; break
  fi
  # Retrying DNS for minutes does not fix a missing record. Other failures may
  # clear while Caddy obtains a certificate or the backend becomes ready.
  [[ $curl_code -ne 6 ]] || break
  sleep 2
done
[[ $ready -eq 1 ]] || { diagnose https --curl-code "$curl_code" --http-status "$((10#${status:-000}))"; exit 1; }
curl_code=0
status="$(curl -sS --connect-timeout 5 --max-time 10 -o /dev/null -w '%{http_code}' "https://${domain}/admin" 2>"$probe/error")" || curl_code=$?
[[ $curl_code -eq 0 && "$status" == 401 ]] || { diagnose https --auth --curl-code "$curl_code" --http-status "$((10#${status:-000}))"; exit 1; }
profiles="$(manage get COMPOSE_PROFILES)"
if [[ ",$profiles," == *,wireguard,* ]]; then
  wg_domain="$(manage get WG_DOMAIN)"
  curl_code=0
  status="$(curl -sS --connect-timeout 5 --max-time 10 -o /dev/null -w '%{http_code}' "https://${wg_domain}/" 2>"$probe/error")" || curl_code=$?
  [[ $curl_code -eq 0 && "$status" == 401 ]] || { diagnose https --auth --target wireguard --curl-code "$curl_code" --http-status "$((10#${status:-000}))"; exit 1; }
fi
if manage check-protocols; then :; else diagnose stage --phase health; exit 1; fi
if [[ $quiet -eq 0 ]]; then
  manage compose ps
  echo "Services, TLS and authentication checks passed. VPN client handshake still requires an external test."
fi
