#!/usr/bin/env bash
set -euo pipefail
echo "=== Docker ==="; docker ps || true
echo; echo "=== Caddy (tail) ==="; docker logs --tail 80 $(docker ps --format '{{.Names}}' | grep caddy) || true
echo; echo "=== Xray (tail) ==="; docker logs --tail 80 $(docker ps --format '{{.Names}}' | grep xray) || true
echo; echo "=== strongSwan status ==="; ipsec statusall || true
echo; echo "=== UFW status ==="; ufw status verbose || true
