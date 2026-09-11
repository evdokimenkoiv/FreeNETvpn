#!/usr/bin/env bash
set -Eeuo pipefail
amneziawg-go -f awg0 &
vpn_pid=$!
trap 'kill "$vpn_pid" 2>/dev/null || true; wait || true' EXIT
trap 'exit 0' TERM INT
for ((i=0; i<50; i++)); do
  [[ -S /var/run/amneziawg/awg0.sock ]] && break
  sleep 0.1
done
awg setconf awg0 /config/awg0.conf
ip address add "${AWG_ADDRESS:-10.98.0.1/24}" dev awg0
ip link set awg0 mtu 1280 up
if [[ ${AWG_CLIENT:-false} != true ]]; then
  iptables -t nat -A POSTROUTING -s 10.98.0.0/24 -j MASQUERADE
  iptables -A FORWARD -i awg0 -j ACCEPT
  iptables -A FORWARD -o awg0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
fi
wait "$vpn_pid"
