#!/usr/bin/env bash
set -euo pipefail
read -rp "IKEv2 username: " U
read -rsp "Password: " P; echo
echo "${U} : EAP \"${P}\"" >> /etc/ipsec.secrets
systemctl restart strongswan-starter
echo "User ${U} added."
