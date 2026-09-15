#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cp /config/ipsec.conf /etc/ipsec.conf
cp /config/ipsec.secrets /etc/ipsec.secrets
mkdir -p /etc/ppp /etc/xl2tpd /run/xl2tpd
cp /config/chap-secrets /etc/ppp/chap-secrets
cp /config/options.xl2tpd /etc/ppp/options.xl2tpd
cp /config/xl2tpd.conf /etc/xl2tpd/xl2tpd.conf
# Do not expose plaintext L2TP, including to other containers.
iptables -A INPUT -p udp --dport 1701 -m policy --dir in --pol ipsec -j ACCEPT
iptables -A INPUT -p udp --dport 1701 -j DROP
iptables -t nat -A POSTROUTING -s 10.99.0.0/24 -m policy --dir out --pol none -j MASQUERADE
iptables -t nat -A POSTROUTING -s 10.99.1.0/24 -j MASQUERADE
iptables -A FORWARD -s 10.99.0.0/24 -j ACCEPT
iptables -A FORWARD -s 10.99.1.0/24 -j ACCEPT
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
ipsec start --nofork &
ipsec_pid=$!
l2tp_pid=""
if [[ ${ENABLE_L2TP:-false} == true ]]; then
  xl2tpd -D &
  l2tp_pid=$!
fi
cleanup() {
  kill "$ipsec_pid" ${l2tp_pid:+"$l2tp_pid"} 2>/dev/null || true
  wait || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT
wait -n
exit 1
