#!/usr/bin/env bash
# FreeNETvpn: comprehensive health check
# Usage: sudo bash scripts/health_check.sh [-q]
set -euo pipefail
QUIET=0
[[ "${1:-}" == "-q" ]] && QUIET=1

say(){ [[ $QUIET -eq 1 ]] || echo -e "$@"; }

# Load env
if [[ -f .env ]]; then
  set -o allexport; source .env; set +o allexport
else
  say "WARN: .env not found, using defaults"; DOMAIN="${DOMAIN:-localhost}"
fi

# 0) Basics
say "== System =="
uname -a || true
command -v docker >/dev/null || { echo "ERROR: docker not found"; exit 1; }
systemctl is-active docker >/dev/null || { echo "ERROR: docker not active"; exit 1; }
say "Docker OK"

# 1) Docker services
say "\n== Containers =="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

need_up=("caddy" "admin" "xray")
if docker ps --format '{{.Names}}' | grep -q wg-easy; then need_up+=("wg-easy"); fi
if docker ps --format '{{.Names}}' | grep -q outline; then need_up+=("outline"); fi
for n in "${need_up[@]}"; do
  docker ps --format '{{.Names}} {{.Status}}' | grep -E "^${n}\b" >/dev/null || { echo "ERROR: container ${n} not running"; exit 2; }
done
say "Containers OK"

# 2) TLS via Caddy
say "\n== TLS / Caddy =="
host="${DOMAIN:-localhost}"
curl -fsSIk "https://${host}/" >/dev/null && say "HTTPS endpoint reachable" || { echo "ERROR: https://${host}/ unreachable"; exit 3; }
# show cert subject/issuer/expiry (no exit on fail)
echo | openssl s_client -servername "${host}" -connect "127.0.0.1:443" 2>/dev/null | openssl x509 -noout -subject -issuer -enddate || true

# 3) Admin panel / Routes
say "\n== Routes =="
for path in / /admin /wg /outline ; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Host: ${host}" "https://127.0.0.1${path}")
  say "GET ${path} -> ${code}"
done

# 4) Xray internal port
say "\n== Xray =="
docker exec "$(docker ps --format '{{.Names}}' | grep xray)" ss -ltpn | grep 10000 && say "Xray listening on 10000" || echo "WARN: xray port check failed"

# 5) WireGuard (if exists)
if docker ps --format '{{.Names}}' | grep -q wg-easy; then
  say "\n== WireGuard =="
  docker exec "$(docker ps --format '{{.Names}}' | grep wg-easy)" wg show || echo "WARN: wg show failed (no interfaces yet?)"
fi

# 6) IPsec/L2TP (if installed)
say "\n== IPsec/L2TP =="
if command -v ipsec >/dev/null; then ipsec status || true; else say "strongSwan not installed (OK if not selected)"; fi
if systemctl list-unit-files | grep -q xl2tpd.service; then systemctl -q is-active xl2tpd && say "xl2tpd active" || echo "WARN: xl2tpd not active"; fi

# 7) Firewall
say "\n== Firewall (UFW) =="
ufw status verbose || true

say "\nAll checks completed."
