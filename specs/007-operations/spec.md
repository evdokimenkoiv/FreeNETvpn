# Feature Specification: Traffic and server operations

Created: 2026-09-15. Status: implementation and validation.

## User Scenarios & Testing
### US1 — Observe usage (P1)
Administrators inspect service traffic, rates, history and active connections without confusing profiles with online devices.
**US1/AC1:** The portal shows measured counters with timestamps and connection semantics; stopped or failed collectors show unavailable, shared IPsec traffic appears once, and counter resets never produce negative rates.
### US2 — Maintain the server (P1)
Administrators inspect disk space, preview bounded cleanup and check updates without changing running software.
**US2/AC1:** Cleanup requires an unexpired single-use preview, records a job result, preserves VPN state and backups, and members cannot access operations.

## Requirements
- FR-701: Collect bridge-interface RX/TX and TCP inbound socket counts, WireGuard/Amnezia recent handshakes and IKE security associations; label service overhead and shared IPsec traffic explicitly.
- FR-702: Keep at most 24 hours of sampled aggregate history, persist privately, mark gaps/resets and expose unavailable values as null.
- FR-703: Provide admin-only RU/EN traffic and maintenance screens with timestamps, disk usage, reboot hint and read-only project/OS update checks.
- FR-704: Allow only archived journal cleanup older than seven days and dangling Docker build cache older than seven days, with server-side preview tokens and operation history. Never prune volumes, images, containers, profiles or backups.
- SC-701: Parser/reset, authorization, cleanup token/command and browser tests pass; live validation reports sources and limitations.

## Limits
Traffic is service network RX/TX, including both proxy legs and protocol overhead, not billable user payload. TCP sockets are not people; Outline UDP sessions are not counted. IKEv2/L2TP share traffic but report established SAs separately. A recent UDP handshake means seen within 180 seconds, not guaranteed reachability. OS updates use the local APT index and show its age; checks never install software. Cleanup affects host-wide archived system journals or host-wide dangling build cache, explicitly shown before confirmation. Exact reclaimable bytes are unavailable before these tools run; show an estimate/upper bound and actual free-space change afterwards.
