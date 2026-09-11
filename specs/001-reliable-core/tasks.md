# Tasks and evidence

- [x] T001 [US1] Establish principles and requirements in .specify/memory/constitution.md and specs/001-reliable-core/ (FR-008).
- [x] T002 [US1] Add validated configuration and idempotent rendering in tools/manage.py (FR-001/002/004).
- [x] T003 [US1] Repair admin authentication and read-only access in admin/app/main.py (FR-003).
- [x] T004 [US1] Repair installation and SSH-preserving UFW setup in install.sh and scripts/ufw_open_ports.sh (FR-005).
- [x] T005 [US2] Replace obsolete images/configuration in docker-compose.yml and render Caddy/Xray configs (FR-004).
- [x] T006 [US3] Implement backup/restore and VLESS rotation in tools/manage.py (FR-006).
- [x] T007 [US1/US3] Add and pass local regression tests in tests/test_regressions.py.
- [x] T008 [US2] Pass actual TLS/VLESS/WireGuard Linux integration in tests/integration.py on both supported Ubuntu runners (FR-007, SC-003).
- [ ] T009 [US1/US2/US3] Validate installation, DNS/public TLS, off-server traffic, reboot and recovery on a disposable server (SC-005).

Do not mark T009 complete from CI alone. CI tests use isolated Docker networks, test credentials and a private test CA.

Verified 2026-09-11 at commit 992448e27e550837ffd92df28c792141a001377b:
- [CI run](https://github.com/evdokimenkoiv/FreeNETvpn/actions/runs/34622370547): 34 regression tests and shell syntax/lint passed.
- Ubuntu 22.04 and 24.04: authenticated HTTPS and first-run WireGuard setup passed; a real Xray client received the HTTP probe through VLESS/WebSocket/TLS; a kernel WireGuard client recorded a handshake and received the probe through wg0.
- The Docker WireGuard client uses an explicit route to the probe; public internet default routing and DNS remain part of T009.
