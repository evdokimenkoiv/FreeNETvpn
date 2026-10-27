# Feature Specification: Actionable installation failures

Created: 2026-10-27. Status: implementation and validation.

## User Scenarios & Testing
### US1 — Correct input before installation (P1)
An operator understands why VPN and WireGuard UI need distinct hostnames and corrects an invalid entry before entering a password.
**US1/AC1:** Duplicate domains are identified as configuration errors, not DNS failures; interactive input retries the offending field and noninteractive input fails without writing state or reading a password.
### US2 — Recover from a failed installation (P1)
An operator distinguishes unresolved DNS, connection/timeout, TLS verification, backend and authentication failures, fixes the reported issue and resumes without losing identities.
**US2/AC1:** Each supported error shows a stable code, observed evidence, corrective steps and an explicit check/resume command reflecting whether .env exists.

## Requirements
- FR-801: Validate domain syntax and distinctness before password entry; show an example secondary name and preserve existing configuration.
- FR-802: Check the server resolver before Docker setup, report IPv4 addresses and IPv6 warnings without claiming global DNS propagation or guessing the server IP.
- FR-803: Classify HTTPS curl/HTTP failures and installation stages without exposing command arguments, credentials, .env contents or raw logs.
- FR-804: Supply RU/EN recovery guidance and commands for missing versus saved configuration; diagnostic checks do not mutate the installation.
- SC-801: Regression tests cover duplicate/syntax correction, no password/state side effects, DNS failure/timeout, HTTPS categories, shell failure propagation and safe resumption.

## Boundaries
Two different hostnames may share the same public IPv4. The resolver check cannot prove authoritative-zone propagation or inbound provider-firewall access. No DNS records, credentials, ports, operating system or production service changes are made by diagnostics. No automatic reset or insecure TLS fallback. Existing native-client acceptance gates remain unchanged.
