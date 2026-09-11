#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ ${EUID} -eq 0 ]] || { echo "Run as root"; exit 1; }
manage validate
# Establish every configured SSH port before enabling the firewall. Never edit sshd.
ssh_config="$(sshd -T)"
mapfile -t ssh_ports < <(printf '%s\n' "$ssh_config" | awk '$1 == "port" {print $2}')
if [[ -n "${SSH_CONNECTION:-}" ]]; then
  read -r _ _ _ active_port <<<"$SSH_CONNECTION"
  ssh_ports+=("$active_port")
fi
[[ ${#ssh_ports[@]} -gt 0 ]] || { echo "Cannot establish SSH ports; firewall unchanged"; exit 1; }
for port in "${ssh_ports[@]}"; do
  [[ "$port" =~ ^[0-9]+$ && "$port" -gt 0 && "$port" -le 65535 ]] || { echo "Invalid SSH port"; exit 1; }
done
for port in "${ssh_ports[@]}"; do ufw allow "${port}/tcp" comment 'SSH retained by FreeNETvpn'; done
ufw allow 80/tcp
ufw allow 443/tcp
profiles="$(manage get COMPOSE_PROFILES)"
if [[ ",$profiles," == *,wireguard,* ]]; then
  ufw allow "$(manage get WG_PORT)/udp"
fi
if [[ ",$profiles," == *,ikev2,* || ",$profiles," == *,l2tp,* ]]; then
  ufw allow 500/udp
  ufw allow 4500/udp
fi
if [[ ",$profiles," == *,outline,* ]]; then
  ufw allow "$(manage get OUTLINE_PORT)/tcp"
  ufw allow "$(manage get OUTLINE_PORT)/udp"
fi
if [[ ",$profiles," == *,amnezia,* ]]; then ufw allow "$(manage get AWG_PORT)/udp"; fi
ufw --force enable
echo "Firewall rules added; SSH configuration and existing rules preserved."
