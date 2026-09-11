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

Amnezia means the self-hosted AmneziaWG protocol and compatible clients, not the complete Amnezia desktop application's SSH server manager. Outline management is local CLI; its API port is loopback-only. The first supported platform for the official Outline image is x86_64 Linux.
