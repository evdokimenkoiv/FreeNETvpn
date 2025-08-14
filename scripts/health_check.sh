#!/usr/bin/env bash
set -euo pipefail

QUIET=0; [[ "${1:-}" == "-q" ]] && QUIET=1
say(){ [[ $QUIET -eq 1 ]] || echo -e "$@"; }

if [[ -f .env ]]; then set -o allexport; source .env; set +o allexport; fi
host="${DOMAIN:-localhost}"

say "== System =="; uname -a || true
command -v docker >/dev/null || { echo "ERROR: docker not found"; exit 1; }
systemctl is-active docker >/dev/null || { echo "ERROR: docker not active"; exit 1; }
say "Docker OK"

say "\n== Containers =="; docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
need=("caddy" "admin" "xray")
for c in wg-easy outline; do docker ps --format '{{.Names}}' | grep -q "^$c$" && need+=("$c"); done
for n in "${need[@]}"; do docker ps --format '{{.Names}} {{.Status}}' | grep -E "^${n}\b" >/dev/null || { echo "ERROR: container ${n} not running"; exit 2; }; done
say "Containers OK"

say "\n== TLS / Caddy =="
curl -fsSIk "https://${host}/" >/dev/null && say "HTTPS endpoint reachable" || { echo "ERROR: https://${host}/ unreachable"; exit 3; }
echo | openssl s_client -servername "${host}" -connect "127.0.0.1:443" 2>/dev/null | openssl x509 -noout -subject -issuer -enddate || true

say "\n== Routes =="; for path in / /admin /wg /outline; do code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Host: ${host}" "https://127.0.0.1${path}"); say "GET ${path} -> ${code}"; done
say "\n== Xray =="; docker exec "$(docker ps --format '{{.Names}}' | grep xray)" ss -ltpn | grep 10000 && say "Xray listening on 10000" || echo "WARN: xray port check failed"
if docker ps --format '{{.Names}}' | grep -q wg-easy; then say "\n== WireGuard =="; docker exec "$(docker ps --format '{{.Names}}' | grep wg-easy)" wg show || echo "WARN: wg show failed"; fi

say "\n== IPsec/L2TP =="; command -v ipsec >/dev/null && ipsec status || say "strongSwan not installed (OK if not selected)"
systemctl list-unit-files | grep -q xl2tpd.service && systemctl -q is-active xl2tpd && say "xl2tpd active" || true

say "\n== Firewall (UFW) =="; ufw status verbose || true
say "\nAll checks completed."
