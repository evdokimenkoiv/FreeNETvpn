# Tasks and evidence

- [x] T001 Implement responsive local dashboard, login, CSRF and authenticated API.
- [x] T002 Implement restricted Unix agent, systemd installation and persistent operations.
- [x] T003 Integrate named clients/exports/revocation across existing protocols.
- [x] T004 Implement three VLESS and three AWG presets with key preservation.
- [x] T005 Cover credentials, CSRF, allowlists, idempotency, exports, rollback and migration with regression tests.
- [x] T006 Verify real systemd-agent/WireGuard operations and all preset traffic on Ubuntu 22.04/24.04.
- [x] T007 Verify desktop/mobile browser journeys and inspect screenshots.
- [x] T008 Document use, upgrade, architecture, limits and acceptance.
- [ ] External VPS acceptance: public certificates/ports, native mobile applications, DNS/egress, host reboot and restore.

Core implementation `d19ac170d85eb2be18fad740ec10e6d20ba13440` passed [CI 34630194597](https://github.com/evdokimenkoiv/FreeNETvpn/actions/runs/34630194597): 75 regression tests on Linux; both Ubuntu versions passed actual WireGuard/IKEv2/L2TP/Outline/AWG traffic and all six template traffic tests, plus dashboard login/CSRF, native WireGuard create/export/revoke and VLESS create/export/QR/revocation through the real systemd agent.

`tests/ui.cjs` tests desktop/mobile login, navigation, six template cards, create/download/change/revoke, escaping, and recovery after an API outage. Its screenshots use clearly simulated `vpn.example.test` data; they are visual evidence, not live-server telemetry. Final PR checks rerun this browser test alongside Linux integration, including service stop/start and asynchronous backup/download.

Spec/plan/implementation cross-check: FR-01/07 map to browser journeys and actual overview data; FR-02/03 to API tests and real Unix-agent integration; FR-04 to queue/locking tests; FR-05/06 to lifecycle and real packet tests. No unverified VPS outcome is marked complete.
