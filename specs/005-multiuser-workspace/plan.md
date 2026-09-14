# Implementation plan

Keep the read-only/non-root FastAPI container and token-protected Unix agent. Add tools/accounts.py with PBKDF2 hashes, random session revisions and atomic mode-0600 persistence in data/control/accounts.json; serialize changes with the existing operation lock. The .env owner remains a protected administrator. No public signup, generic command execution, writable web volume or new dependency.

Gate every HTTP endpoint by role. Filter member snapshots with an allowlist. Bind assignments to non-secret credential identity digests, not names; the agent rechecks enabled accounts and current profile identity under the operation lock immediately before export. Both Basic and cookie authentication follow the same policy. Existing owner credentials and protocol configuration remain unchanged. Account JSON is inside the existing offline backup boundary.

Use local vanilla JS/CSS and paired RU/EN content; no CDN or third-party script. Separate admin and member navigation. Reuse existing asynchronous jobs. Account forms provide roles, explicit profile assignments, reset/disable/delete and audit history. Guides are selected by five devices and protocol with official links and compatibility notes. Screenshots use tests/ui.cjs demonstration fixtures only.

Validation: tests/test_accounts.py and actual Unix-handler tests for isolation/revisions; existing regressions/contract tests; account backup roundtrip; Playwright CRUD, member journeys, bilingual guides, mobile layout and screenshots. Preserve protocol packet CI matrices. Deployment follows a pre-upgrade backup, code update, root-agent restart and rebuilt admin container; verify roles over public HTTPS, then remove temporary acceptance accounts.

Constitution check: preserves credentials/data; privileged work stays behind fixed agent methods; all anonymous/admin/member routes covered; backups include accounts; secrets excluded from docs and screenshots. No exceptions.
