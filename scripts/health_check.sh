#!/usr/bin/env bash
set -euo pipefail
QUIET=0; [[ "${1:-}" == "-q" ]] && QUIET=1
say(){ [[ $QUIET -eq 1 ]] || echo -e "$@"; }
if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; else DOMAIN="${DOMAIN:-localhost}"; fi
say "== Docker =="; command -v docker >/dev/null || { echo "ERROR: docker not found"; exit 1; }
systemctl is-active docker >/dev/null || { echo "ERROR: docker not active"; exit 1; }
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
need=("caddy" "admin" "xray"); for n in "${need[@]}"; do docker ps --format '{{.Names}} {{.Status}}' | grep -E "^${n}\b" >/dev/null || { echo "ERROR: ${n} not running"; exit 2; }; done
say "\n== TLS / Caddy =="
host="${DOMAIN:-localhost}"
curl -fsSIk "https://${host}/" >/dev/null && say "HTTPS OK" || { echo "ERROR: https://${host}/ unreachable"; exit 3; }
echo | openssl s_client -servername "${host}" -connect "127.0.0.1:443" 2>/dev/null | openssl x509 -noout -subject -issuer -enddate || true
say "\n== Routes =="
for path in / /admin /wg /outline ; do code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Host: ${host}" "https://127.0.0.1${path}"); say "GET ${path} -> ${code}"; done
say "\n== Xray =="
docker exec "$(docker ps --format '{{.Names}}' | grep xray)" ss -ltpn | grep 10000 && say "Xray listening on 10000" || echo "WARN: xray check failed"
if docker ps --format '{{.Names}}' | grep -q wg-easy; then say "\n== WireGuard =="; docker exec "$(docker ps --format '{{.Names}}' | grep wg-easy)" wg show || echo "WARN: wg show failed"; fi
say "\n== IPsec/L2TP =="
command -v ipsec >/dev/null && ipsec status || say "strongSwan not installed"
systemctl list-unit-files | grep -q xl2tpd.service && systemctl -q is-active xl2tpd && say "xl2tpd active" || true
say "\n== UFW =="; ufw status verbose || true
say "\nHealth check finished."
