#!/usr/bin/env bash
set -Eeuo pipefail
domain="${1:?Usage: check_public_ip.sh domain}"
public4="$(curl -4 -fsS --connect-timeout 5 --max-time 10 https://api.ipify.org || true)"
addresses="$(getent ahostsv4 "$domain" | awk '{print $1}' | sort -u || true)"
[[ -n "$public4" && -n "$addresses" ]] || { echo "Could not verify DNS/public IPv4"; exit 1; }
grep -Fxq "$public4" <<<"$addresses"
