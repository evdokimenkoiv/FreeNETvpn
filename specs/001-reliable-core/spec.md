# Reliable FreeNETvpn core

> Исторический этап разработки. Актуальное расширение: [003 — кабинет и шаблоны](../003-dashboard-presets/spec.md). Ограничение «read-only panel» заменено разрешёнными операциями через локальный агент; требования сохранности данных и запрет общего command API действуют. Все шесть протоколов восстановлены в [этапе 002](../002-all-protocols/spec.md).

Status: code and Linux integration verified; external VPS acceptance partial | Created: 2026-09-11

## Scope

Original stage scope (protocol restoration is now delivered by 002; administrative writes by 003): repair the runnable core: WireGuard (wg-easy), VLESS over WebSocket/TLS, protected administration, installation, backup and recovery. Preserve historical integrations separately. IKEv2/L2TP/Outline/Amnezia are not advertised as working in this stabilization release; restoring all of them is a separate scope decision. At this original stage no production server access was supplied. Subsequent Ubuntu 26.04 deployment evidence and remaining limits are recorded in docs/vps-qualification.md.

## User scenarios and acceptance

### US1 — Install and open the panel (P1)

**US1/AC1:** Given Ubuntu 22.04/24.04/26.04, a public IPv4, two DNS names and open HTTPS/UDP ports, installing creates the complete project, validates configuration, starts selected services and exposes authenticated HTTPS administration. Wrong/missing credentials return 401. SSH access settings remain unchanged.

### US2 — Connect VPN clients (P1)

**US2/AC1:** Given a configured server, when WireGuard users complete the protected setup wizard, create/export a peer and exchange packets through an authenticated WireGuard tunnel. VLESS users export an encoded URI and exchange packets through WebSocket and certificate-validated TLS. Both protocols must have an automated packet test.

### US3 — Repeat installation and recover data (P1)

**US3/AC1:** Given an existing installation, when configuration is repeated, it preserves credentials, UUIDs and client data. A consistent offline backup restores to an empty installation. Restore rejects traversal, links and unexpected files. Rotation creates a backup and restores old VLESS settings if validation/start fails.

## Requirements

- FR-001: Validate configuration as data; reject unsupported profiles and malformed inputs.
- FR-002: Preserve all existing keys/data on ordinary installation and reconfiguration.
- FR-003: Require authentication for administrative reads, backups and the WireGuard setup wizard.
- FR-004: Render concrete Xray/Caddy configurations; preserve WebSocket/admin paths; expose the configured WireGuard UDP port.
- FR-005: Never automatically modify SSH authentication or port. Add SSH allow rules before enabling UFW.
- FR-006: Provide restart-safe, secret-inclusive backups and non-overwriting restore.
- FR-007: Fail CI on lint, unit or integration failures.
- FR-008: Clearly label legacy features and external acceptance still pending.

## Success criteria

- SC-001: Protected data reads return 401 without credentials and 200 with valid credentials where data exists. Feature 003 adds writes returning 202 for accepted jobs; /admin serves a 401 login page to anonymous users.
- SC-002: A repeated configure operation leaves .env and representative client data byte-identical.
- SC-003: CI obtains an HTTP payload through VLESS/TLS and through WireGuard, recording a nonzero handshake timestamp.
- SC-004: The backup/restore regression preserves client state and secrets, and rejects malicious archives.
- SC-005: An independent off-server client verifies DNS, public CA, UDP reachability and internet egress before production sign-off. External gate: partially verified; full native-client and recovery acceptance remains open (docs/vps-qualification.md).

## Edge cases

Existing legacy .env, missing DNS, blocked UDP, occupied HTTPS port, wrong admin password, unavailable backend, empty backups, hostile archive names, optional service disabled, failed config validation, failure during rotation. Errors must be explicit and must not report successful deployment.

## Key entities

Validated deployment configuration, generated runtime configuration, persistent client state and offline backup; see data-model.md.
