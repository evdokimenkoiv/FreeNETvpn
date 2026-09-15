# Implementation plan

> Исторический этап разработки. Актуальное расширение: [003 — кабинет и шаблоны](../003-dashboard-presets/spec.md). Ограничение «read-only panel» заменено разрешёнными операциями через локальный агент; требования сохранности данных и запрет общего command API действуют.

Use one strongSwan/xl2tpd container for IKEv2 and L2TP to share UDP 500/4500. Use the official Outline shadowbox image pinned by digest, management TLS on loopback, and a fixed published data port. Build official AmneziaWG Go/tools at pinned commits; use userspace TUN so host kernels need no custom module.

Keep protocol secrets and client exports under data/, configuration under runtime/, and control operations in the standard-library Python CLI. Include these paths in the existing offline backup. Keep the web panel read-only. Extend installation, firewall rules and protocol selection without regenerating old secrets.

Validation: regressions and shell lint; real IPsec/PPP, Shadowsocks and AmneziaWG clients in disposable Docker networks on Ubuntu 22.04 and 24.04. Report external DNS/firewall/CA/reboot/client-platform acceptance separately.

Upstream references: https://docs.strongswan.org/docs/latest/config/IKEv2.html, https://github.com/OutlineFoundation/outline-server, https://github.com/amnezia-vpn/amneziawg-go, https://github.com/amnezia-vpn/amneziawg-tools.

## Technical context and project structure

Python 3.12 for development/CI; stdlib management and Spec Kit helper scripts; FastAPI admin with pinned dependencies; Docker Compose and systemd on Ubuntu 22.04/24.04/26.04 x86_64 for runtime. Ubuntu 26.04 host qualification is recorded separately in docs/vps-qualification.md; the packet CI matrix remains 22.04/24.04. Windows supports development checks, not the VPN server runtime. Sources live in tools/, admin/, services/ and scripts/; tests/ contains regression, browser and Linux traffic suites. No runtime dependency on Specify CLI.

## Design artifacts

- research.md records decisions and rejected alternatives.
- data-model.md defines ownership, secret boundaries and invariants.
- contracts/ defines this feature's external interface; 003 owns the cabinet/agent contract.
- quickstart.md gives the repeatable validation path.

## Phases and constitution check

Setup establishes artifact/dependency inputs; foundation validates ownership/security; each prioritized story is implemented and independently verified; final cross-cutting checks preserve historical evidence and external acceptance. tasks.md lists exact source/test paths and dependencies. All six constitution principles apply: reproducible checks; preserve existing secrets/data; authenticated administration without arbitrary commands; validate configuration as data; failing CI; secret-free Git and explicit external limitations. No exception is requested.
