# Restore all advertised VPN protocols

> Исторический этап разработки. Актуальное расширение: [003 — кабинет и шаблоны](../003-dashboard-presets/spec.md). Ограничение «read-only panel» заменено разрешёнными операциями через локальный агент; требования сохранности данных и запрет общего command API действуют.

User request: restore IKEv2, L2TP/IPsec, Outline and Amnezia alongside the verified WireGuard/VLESS core.

## Requirements

- FR-201: IKEv2 authenticates the server certificate and EAP clients, assigns addresses and routes client traffic.
- FR-202: L2TP uses authenticated PPP inside IPsec transport; plaintext UDP 1701 is not publicly exposed and is dropped without IPsec.
- FR-203: Outline uses the official server image, locally authenticated TLS management and creates/exports/revokes client keys.
- FR-204: AmneziaWG builds pinned official sources, exports matching obfuscation parameters and routes actual client traffic.
- FR-205: Protocol selection, ports, installation, backups and client operations preserve existing state. Existing v2 configuration remains readable.
- FR-206: Each restored protocol has a successful real Linux traffic test on both supported Ubuntu versions. External VPS acceptance remains separately recorded.

## Acceptance

Create a client, export credentials, connect, exchange an HTTP payload, restart without changing credentials and revoke access. Malformed names, duplicate clients, invalid/conflicting ports and inactive protocol operations fail explicitly. Secret files are never published or placed in the unauthenticated web root.

## Boundaries

Amnezia means the self-hosted AmneziaWG protocol and compatible clients, not the complete Amnezia desktop application's SSH server manager. Outline management uses the local CLI and the allowlisted dashboard agent from feature 003; its API port is loopback-only. The first supported platform for the official Outline image is x86_64 Linux.

## User stories and acceptance scenarios

### US1 — Connect IKEv2 and L2TP clients (P1)

Independent test: tests/integration_extra.py creates both clients and requests an HTTP payload through IPsec and PPP.

- **US1/AC1:** Given enabled IKEv2 and an exported CA/credential bundle, when a client authenticates the server and EAP identity, then it receives a virtual IP and routes a request through the CHILD_SA.
- **US1/AC2:** Given enabled L2TP, when a client authenticates IPsec and PPP, then tunneled HTTP succeeds; unprotected UDP 1701 is rejected.

### US2 — Connect Outline and AmneziaWG clients (P1)

Independent test: tests/integration_extra.py tests each protocol before/after restart and after revocation.

- **US2/AC1:** Given an enabled protocol, when a named key is created/exported, then a compatible client receives an HTTP payload; restarting preserves the key and revocation rejects subsequent access.

### US3 — Preserve configuration and recover clients (P1)

Independent test: tests/test_protocols.py backs up and restores protocol secrets and reads old v2 configuration.

- **US3/AC1:** Given existing v2 data, when defaults are read, preparation is repeated or a backup is restored to an empty target, then existing keys and credentials remain unchanged; invalid names, duplicate clients and conflicting ports fail explicitly.

## Success criteria

- SC-201: Both Ubuntu 22.04 and 24.04 pass IKEv2 certificate/EAP/CHILD_SA and L2TP IPsec/PPP HTTP tests, including rejection of plaintext L2TP.
- SC-202: Both Ubuntu baselines pass Outline and AmneziaWG HTTP traffic before/after restart and reject revoked clients.
- SC-203: Regression tests preserve existing configuration, PKI and client secrets through repeat preparation and backup/restore.
- SC-204: Before production sign-off, an independent VPS test verifies public ports, native client applications, reboot and recovery using docs/acceptance.md. External gate: pending.

## Edge cases and key entities

Missing PPP/TUN, unsupported architecture, API unavailability, duplicate names, port conflicts, inactive protocols, legacy v2 config and partial key creation must yield explicit failures and preserve existing state. ProtocolState, Client, PKI and export ownership are defined in data-model.md.
