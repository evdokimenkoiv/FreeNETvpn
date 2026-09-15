#!/usr/bin/env bash
set -euo pipefail
read -rp "L2TP username: " U
read -rsp "Password: " P; echo
echo "${U} * ${P} *" >> /etc/ppp/chap-secrets
systemctl restart xl2tpd || true
echo "User ${U} added."
