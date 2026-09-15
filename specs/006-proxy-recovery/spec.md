# Feature Specification: Proxies and recovery

Created: 2026-09-14. Status: implementation and validation.

## User Scenarios & Testing
### US1 — Issue proxy access (P1)
Administrators create individual MTProto and HTTP CONNECT/SOCKS5 profiles and assign them through the existing account permissions.
**US1/AC1:** A member downloads only assigned credentials; authorized HTTP/SOCKS traffic succeeds, missing/wrong/revoked credentials fail, and internal destinations are blocked.
### US2 — Recover a server (P1)
The administrator downloads an off-server backup and follows an explicit empty-target recovery procedure.
**US2/AC1:** Restore preserves accounts, assignments and proxy secrets, rejects an occupied target, and explains how to start and verify the recovered installation.

## Requirements
- FR-601: Add optional MTProto with individual random secrets, Telegram import links and a documented 16-profile upstream limit.
- FR-602: Add authenticated HTTP CONNECT and SOCKS5 with independent random profile passwords, no anonymous mode, no UDP, and blocked non-public destinations.
- FR-603: Integrate both services into existing lifecycle, permissions, exports, firewall and RU/EN device guides.
- FR-604: Show explicit empty-target restore steps in the backup screen and bilingual documentation; retain all account and proxy state in backups.
- SC-601: Automated authentication, revocation, configuration and backup tests pass; report live checks separately from native Telegram use.
- SC-602: External gate: Native Telegram acceptance on a user's device remains recorded separately from server/TCP readiness.

## Assumptions and limits
Proxy services are optional for existing/fresh installations; `services all` enables them. HTTP/SOCKS authentication is not encrypted on the wire: use VPN transport on untrusted networks. MTProto serves Telegram only, without sponsor tags. Recovery is server-side and never overwrites the running installation from the browser. Maintain the same source revision for restore, then verify DNS, TLS and real client traffic.
