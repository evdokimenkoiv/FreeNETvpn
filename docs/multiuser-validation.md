# Multiuser workspace validation / Проверка многопользовательского кабинета

Scope: feature 005, 2026-09-14. Account lifecycle, protected installation owner, per-profile permissions, bilingual UI, device guides and public demonstration images. Previous native VPN acceptance limits remain in acceptance.md and vps-qualification.md; this feature does not claim to retest every device/protocol network path.

Feature 006: `tests/integration_proxy.py` tests actual HTTP/SOCKS HTTPS traffic and denial, MTProxy packet parsing with correct/unknown/revoked secrets, then a Telegram resPQ nonce roundtrip. GitHub-hosted runners use explicit `--local-mtproto`: their Telegram roundtrip timed out even after NAT and startup corrections, so CI asserts MTProxy authentication through upstream daemon counters (forwarded + dropped parsed queries) and does not claim Telegram reachability. The default full command passed on the deployment VPS; repeat it and an external transport probe before release. Native Telegram app acceptance remains separate. No failed network probe is relabeled as successful.

Security cases: regular users cannot access users, backups, jobs, server status, native wg-easy or another account's exports/QR. Basic authentication follows the same checks. Password changes, disable/delete and role changes invalidate old sessions; recreated usernames/profile names cannot inherit prior access. The root agent rechecks assignment identity before exports. Account backup/restore preserves hashes, assignments and audit records.

Browser: admin creates/edits/assigns/deletes an account; existing six-preset client lifecycle still passes; member view has no administrative navigation; all five device guides are selectable; RU/EN switching and mobile layout are checked. Screenshot fixtures contain no real host data or keys.

Run `python -m pytest -q`, `python tools/spec_audit.py`, `python tools/check_spec_contexts.py` and `node tests/ui.cjs`. Current commit checks are available on PR #1. Unix-agent and real packet tests run on Linux CI; Windows skips only platform-specific tests. Deploy only after the exact commit's required checks pass, with a pre-upgrade backup and post-upgrade role checks over HTTPS.

Review findings addressed: identity-bound grants prevent name reuse leakage; every direct backup/QR/forward-auth route is gated; server-derived actor prevents public payload impersonation; session revisions are randomized across account recreation; language switching updates the connection timestamp and status too; portal disabling is explicitly distinguished from VPN key revocation.

Русский: проверяются создание и удаление аккаунтов, права на API/скачивание/QR, немедленная инвалидизация сессий, сохранность аккаунтов в архиве, два языка, пять семейств устройств и мобильная вёрстка. Скриншоты основаны на демонстрационных данных. Полная сетевая приёмка нативных VPN-клиентов из прошлых этапов остаётся отдельной задачей.
