# Tasks: 003-dashboard-presets

Generated using the official Spec Kit 1.0.6 task workflow and resolved template. Historical numbering/evidence for features 001–003 is retained in implementation-history.md. Completion below is based on verified current code; external acceptance stays open.

## Phase 1: Setup

- [x] T001 Retain local frontend assets and secret-free repository boundaries in `admin/app/static/app.js`, `.gitignore` (FR-301 FR-302).

## Phase 2: Foundational

- [x] T002 Implement restricted Unix agent, bounded persistent jobs and serialized writes in `tools/control_agent.py`, `tools/control.py`, `tools/operation_lock.py`, `scripts/install_control.sh` (FR-303 FR-304).

## Phase 3: US1

Goal: deliver US1 as declared in spec.md (P1). Independent validation: `tests/test_dashboard.py::test_session_csrf_logout_and_secret_exclusion`.

- [x] T003 [US1] Provide responsive login, private overview, CSRF protection and explicit stale service state in `admin/app/main.py`, `admin/app/static/app.js`, `admin/app/static/app.css`, `tools/control.py` (FR-301 FR-302 FR-307 SC-301 SC-302 US1/AC1).

## Phase 4: US2

Goal: deliver US2 as declared in spec.md (P1). Independent validation: `tests/integration.py`.

- [x] T004 [US2] Create/export/find/revoke named clients while preserving the legacy VLESS user in `tools/control.py`, `tools/protocols.py`, `admin/app/static/app.js` (FR-305 SC-303 US2/AC1).

## Phase 5: US3

Goal: deliver US3 as declared in spec.md (P1). Independent validation: `tests/test_dashboard.py::test_vless_failed_validation_rolls_back`.

- [x] T005 [US3] Implement three VLESS and three AWG presets; retain UUID/private keys and server S/H fields; roll back invalid VLESS changes in `tools/presets.py`, `tools/protocols.py` (FR-305 FR-306 SC-303 US3/AC1).

## Phase 6: US4

Goal: deliver US4 as declared in spec.md (P1). Independent validation: `tests/test_dashboard.py::test_service_allowlist_and_snapshot_redaction`.

- [x] T006 [US4] Control allowlisted services and show shared IKEv2/L2TP impact and job results in `tools/control.py`, `admin/app/static/app.js` (FR-303 FR-304 SC-303 US4/AC1).

## Phase 7: US5

Goal: deliver US5 as declared in spec.md (P1). Independent validation: `tests/integration.py`.

- [x] T007 [US5] Create a backup through the persistent worker and retrieve it after web restart in `tools/control.py`, `tools/manage.py`, `admin/app/main.py` (FR-304 SC-303 US5/AC1).

## Phase 8: Polish

- [x] T008 Document cabinet limits, preset compatibility and actual verification scope in `docs/dashboard.md`, `docs/acceptance.md` (FR-307).

- [ ] T009 Record independent VPS public CA/ports/native apps/DNS/egress/reboot/restore acceptance (EXTERNAL — pending) in `docs/acceptance.md` (SC-304).

## Dependencies and delivery strategy

Setup → foundation → stories in listed priority order → polish. The first story is the MVP; validate each story before adding the next. Shared files are edited sequentially. Existing implementations are verified rather than replaced. External tasks require an independent VPS and remain open until evidence is recorded.

## Independent work opportunities

After foundation, each story’s test review can be performed independently of other stories. Do not run two mutations of tools/protocols.py or tools/control.py concurrently. No task is marked [P] because the implementation tasks share state or files; read-only reviews of each story’s independent test are the parallel examples.
