# Feature 003: Management dashboard and client presets

Status: implemented; external deployment acceptance remains separate.

## User intent

Provide an attractive, usable cabinet for all six existing VPN protocols, with ready-made AmneziaWG and VLESS configuration templates. Preserve current installations and clients.

## User journeys and acceptance

1. An administrator signs in on desktop or mobile and sees actual server/service state. Invalid credentials fail; anonymous users cannot obtain clients, backups or exports. Disconnection shows an error and marks existing data as stale.
2. The administrator creates a named client, obtains a configuration/download/QR where supported, finds it through search/filter, and revokes it. Revoked VLESS, WireGuard, Outline and AWG clients disappear from server state; packet tests cover revocation where applicable.
3. The administrator chooses one of three VLESS or three AWG templates. Exports describe compatibility and concrete parameters. Existing UUID/private keys and shared AWG S/H values survive a template change. Real HTTP traffic passes for all six presets.
4. The administrator starts/stops/restarts a selected service and sees completion or an actionable failure. Shared IKEv2/L2TP actions explain their common impact.
5. The administrator requests a backup and can retrieve it after services return. The job survives the web-container restart and its history contains no passwords or exported secrets.

## Requirements

- FR-01: Russian responsive interface with overview, searchable clients, template catalog, backups and operation history.
- FR-02: Authenticated sessions, origin/CSRF checks for changes, local assets/QR, no caching of private responses.
- FR-03: Web process remains non-root, read-only and without Docker socket. Root work is restricted to an authenticated local Unix agent with an explicit operation allowlist.
- FR-04: Persistent bounded operation queue/history, deduplication by request ID, explicit interrupted state after agent restart; serialize client writes between CLI and agent.
- FR-05: Named VLESS users retain the original legacy WS user; WS/TLS and gRPC/TLS route through existing Caddy HTTPS. Failed VLESS validation restores previous configuration.
- FR-06: AWG presets change client MTU/keep-alive/J parameters only, keeping compatible server keys/S/H values.
- FR-07: No invented usage or availability metrics. Service state is distinguished from off-server VPN acceptance.

Out of scope: a billing system, multi-server orchestration, end-user accounts, arbitrary configuration/shell editing, destructive restore inside the cabinet, automatic wg-easy first-run completion or promises of regional-filter bypass.

Success criteria: regression/security suite green; desktop and 390px browser journeys pass without overflow or JavaScript errors; actual six-protocol and six-template traffic passes on Ubuntu 22.04/24.04; published evidence identifies CI vs. unperformed VPS acceptance.
