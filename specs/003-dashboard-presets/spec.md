# Feature 003: Management dashboard and client presets

Status: implemented; external deployment acceptance remains separate.

## User intent

Provide an attractive, usable cabinet for all six existing VPN protocols, with ready-made AmneziaWG and VLESS configuration templates. Preserve current installations and clients.

## User journeys and acceptance

### US1 — Sign in and inspect service state (P1)

Independent test: tests/ui.cjs and tests/test_dashboard.py verify login, stale data and privacy.

**US1/AC1:** Given a configured cabinet, when an administrator signs in on desktop or mobile, then they see actual server/service state. Invalid credentials fail; anonymous users cannot obtain clients, backups or exports. Disconnection shows an error and marks existing data as stale.
### US2 — Manage named clients (P1)

Independent test: tests/integration.py verifies native WireGuard and VLESS client lifecycle; tests/integration_extra.py verifies other protocol traffic.

**US2/AC1:** Given an authenticated cabinet, when the administrator creates a named client, obtains a configuration/download/QR where supported, finds it through search/filter, and revokes it, then revoked VLESS, WireGuard, Outline and AWG clients disappear from server state; packet tests cover revocation where applicable.
### US3 — Apply compatible presets (P1)

Independent test: tests/integration.py and tests/integration_extra.py verify HTTP through every preset.

**US3/AC1:** Given an authenticated cabinet, when the administrator chooses one of three VLESS or three AWG templates, then exports describe compatibility and concrete parameters. Existing UUID/private keys and shared AWG S/H values survive a template change. Real HTTP traffic passes for all six presets.
### US4 — Control a selected service (P1)

Independent test: tests/integration.py stops/starts a service and observes its job.

**US4/AC1:** Given an authenticated cabinet, when the administrator starts/stops/restarts a selected service, then they see completion or an actionable failure. Shared IKEv2/L2TP actions explain their common impact.
### US5 — Create and retrieve a backup (P1)

Independent test: tests/integration.py creates a backup through the agent and downloads it after admin recovery.

**US5/AC1:** Given an authenticated cabinet, when the administrator requests a backup, then they can retrieve it after services return. The job survives the web-container restart and its history contains no passwords or exported secrets.

## Requirements

- FR-301: Russian responsive interface with overview, searchable clients, template catalog, backups and operation history.
- FR-302: Authenticated sessions, origin/CSRF checks for changes, local assets/QR, no caching of private responses.
- FR-303: Web process remains non-root, read-only and without Docker socket. Root work is restricted to an authenticated local Unix agent with an explicit operation allowlist.
- FR-304: Persistent bounded operation queue/history, deduplication by request ID, explicit interrupted state after agent restart; serialize client writes between CLI and agent.
- FR-305: Named VLESS users retain the original legacy WS user; WS/TLS and gRPC/TLS route through existing Caddy HTTPS. Failed VLESS validation restores previous configuration.
- FR-306: AWG presets change client MTU/keep-alive/J parameters only, keeping compatible server keys/S/H values.
- FR-307: No invented usage or availability metrics. Service state is distinguished from off-server VPN acceptance.

Out of scope: a billing system, multi-server orchestration, end-user accounts, arbitrary configuration/shell editing, destructive restore inside the cabinet, automatic wg-easy first-run completion or promises of regional-filter bypass.

## Success criteria

- SC-301: Authentication/Origin/CSRF, queue/allowlist, secret-redaction, serialization and preset preservation regression tests pass.
- SC-302: Chromium journeys pass at 1440px and 390px without horizontal overflow or JavaScript errors, including offline recovery.
- SC-303: On Ubuntu 22.04 and 24.04, real HTTPS agent/native WireGuard operations and all six VPN protocols and six presets pass their declared packet checks, plus service control and asynchronous backup/download.
- SC-304: docs/acceptance.md records independent public CA/ports, native applications, DNS/egress, reboot and recovery before production sign-off. External gate: pending.

## Edge cases and key entities

Expired sessions, stale CSRF, rate limits, a full queue, duplicate request IDs, agent restart, disabled protocols, failed VLESS validation, missing native wg-easy setup and interrupted connectivity produce explicit errors without leaking secrets. Client, Preset, Job and Session are defined in data-model.md.

## Identifier migration

FR-01 through FR-07 from the first version are FR-301 through FR-307 respectively; their obligations are unchanged. Features 001/002 are extended by this feature for administrative writes and client presets.
