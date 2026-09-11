FROM debian:12-slim
RUN apt-get update && apt-get install -y --no-install-recommends strongswan strongswan-pki libcharon-extra-plugins libcharon-extauth-plugins libstrongswan-extra-plugins xl2tpd ppp iptables iproute2 curl ca-certificates openssl procps && rm -rf /var/lib/apt/lists/*
COPY start.sh /usr/local/bin/start-vpn
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s CMD ipsec statusall | grep -q 'uptime:'
ENTRYPOINT ["bash", "/usr/local/bin/start-vpn"]
