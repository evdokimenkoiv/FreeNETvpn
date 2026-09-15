# Historical implementation evidence

This is an archived record, not the active task list. Current tasks.md supersedes its numbering.

# Tasks and evidence

> Исторический этап разработки. Актуальное расширение: [003 — кабинет и шаблоны](../003-dashboard-presets/spec.md). Ограничение «read-only panel» заменено разрешёнными операциями через локальный агент; требования сохранности данных и запрет общего command API действуют.

- [x] Define scope and architecture for all protocols.
- [x] Implement services, persistent configuration and client lifecycle.
- [x] Pass configuration/client lifecycle regression tests.
- [x] Pass real IKEv2 and L2TP/IPsec traffic tests on Ubuntu 22.04/24.04.
- [x] Pass real Outline and AmneziaWG traffic tests on Ubuntu 22.04/24.04.
- [x] Update installation, migration, operations and acceptance documentation.
- [ ] External VPS acceptance: public ports, client applications, reboot and recovery.

Verified 2026-09-11: [CI run 34625722643](https://github.com/evdokimenkoiv/FreeNETvpn/actions/runs/34625722643), commit 5b78ee930dbfb7be86f5a671b60ea3742e824d45. Both Ubuntu versions passed the existing WireGuard/VLESS tests and all four new protocol tests. New checks cover IKEv2 server certificate/EAP/CHILD_SA with a virtual-IP-bound HTTP request, IPsec transport + L2TP/MSCHAPv2/PPP traffic, Outline API TLS and Shadowsocks traffic, and AmneziaWG handshake/traffic. Outline and AmneziaWG passed traffic after restart and rejected revoked keys. Regression tests also cover persistent PKI, backups, duplicate clients and malformed names/ports.

The integration test runs in disposable containers. Full host reboot, root installation and independent native client/VPS acceptance remain open; they are not inferred from CI.
