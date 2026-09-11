# Implementation plan

Use one strongSwan/xl2tpd container for IKEv2 and L2TP to share UDP 500/4500. Use the official Outline shadowbox image pinned by digest, management TLS on loopback, and a fixed published data port. Build official AmneziaWG Go/tools at pinned commits; use userspace TUN so host kernels need no custom module.

Keep protocol secrets and client exports under data/, configuration under runtime/, and control operations in the standard-library Python CLI. Include these paths in the existing offline backup. Keep the web panel read-only. Extend installation, firewall rules and protocol selection without regenerating old secrets.

Validation: regressions and shell lint; real IPsec/PPP, Shadowsocks and AmneziaWG clients in disposable Docker networks on Ubuntu 22.04 and 24.04. Report external DNS/firewall/CA/reboot/client-platform acceptance separately.

Upstream references: https://docs.strongswan.org/docs/latest/config/IKEv2.html, https://github.com/OutlineFoundation/outline-server, https://github.com/amnezia-vpn/amneziawg-go, https://github.com/amnezia-vpn/amneziawg-tools.
