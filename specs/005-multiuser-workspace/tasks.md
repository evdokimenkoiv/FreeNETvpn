# Tasks: 005-multiuser-workspace

## Phase 1: Setup
- [x] T001 Describe role and migration scope in `specs/005-multiuser-workspace/spec.md`, `tools/accounts.py` (FR-501).

## Phase 2: Foundational
- [x] T002 Persist account credentials/revisions and identity-bound assignments in `tools/accounts.py`, `tools/control_agent.py`, `tools/control.py` (FR-504).

## Phase 3: US1
- [x] T003 [US1] Deliver account management and protected-owner behavior in `admin/app/main.py`, `tools/accounts.py`, `tests/test_accounts.py` (FR-502 FR-508 US1/AC1).

## Phase 4: US2
- [x] T004 [US2] Enforce endpoint/export/QR isolation in `admin/app/main.py`, `tools/control_agent.py`, `tests/test_accounts.py` (FR-503 SC-501 US2/AC1).

## Phase 5: US3
- [x] T005 [US3] Build bilingual role views and five-device guides in `admin/app/static/app.js`, `admin/app/static/guides.js`, `admin/app/static/app.css`, `tests/ui.cjs` (FR-505 FR-506 SC-502 US3/AC1).

## Phase 6: US4
- [x] T006 [US4] Publish bilingual entrypoints and representative screenshots in `README.md`, `README.ru.md`, `docs/accounts.en.md`, `docs/accounts.ru.md`, `docs/images/README.md` (FR-507 US4/AC1).

## Phase 7: Polish
- [x] T007 Validate account backup, complete contract inventory and browser reproduction in `tests/test_accounts.py`, `tests/test_contracts.py`, `tests/ui.cjs`, `docs/multiuser-validation.md` (SC-503).

## Dependencies
Setup → account storage → role enforcement → role-specific UI → bilingual docs/screenshots → complete tests and deployment. Existing protocol acceptance gates remain separately tracked; this feature does not relabel them as complete.
