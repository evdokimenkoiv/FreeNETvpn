# Tasks: 001-reliable-core

Generated using the official Spec Kit 1.0.6 task workflow and resolved template. Historical numbering/evidence for features 001–003 is retained in implementation-history.md. Completion below is based on verified current code; external acceptance stays open.

## Phase 1: Setup

- [x] T001 Retain constitution and current scope in `.specify/memory/constitution.md`, `specs/001-reliable-core/spec.md` (FR-008).

## Phase 2: Foundational

- [x] T002 Validate configuration as data and preserve existing configuration bytes in `tools/manage.py` (FR-001 FR-002 SC-002).

## Phase 3: US1

Goal: deliver US1 as declared in spec.md (P1). Independent validation: `tests/test_regressions.py::test_administrative_routes_require_auth`.

- [x] T003 [US1] Protect administrative data and the native WireGuard setup wizard in `admin/app/main.py`, `tools/manage.py` (FR-003 SC-001 US1/AC1).

- [x] T004 [US1] Install the complete project while preserving SSH and refusing unrelated targets in `install.sh`, `scripts/ufw_open_ports.sh` (FR-005 US1/AC1).

## Phase 4: US2

Goal: deliver US2 as declared in spec.md (P1). Independent validation: `tests/test_regressions.py::test_rendered_protocol_contract`.

- [x] T005 [US2] Render concrete WireGuard/Xray/Caddy configurations and verify tunnel traffic in `tools/manage.py`, `docker-compose.yml` (FR-004 SC-003 US2/AC1).

## Phase 5: US3

Goal: deliver US3 as declared in spec.md (P1). Independent validation: `tests/test_regressions.py::test_backup_restore_roundtrip_preserves_credentials_and_state`.

- [x] T006 [US3] Create offline backups, reject unsafe or nonempty restores and roll back failed rotation in `tools/manage.py` (FR-006 SC-004 US3/AC1).

## Phase 6: Polish

- [x] T007 Run failing regression, bootstrap, lint and Linux integration gates in `.github/workflows/ci.yml` (FR-007).

- [ ] T008 Record independent VPS installation, DNS/public CA, egress, reboot and recovery acceptance (EXTERNAL — partial; native-client/full recovery checks remain open) in `docs/acceptance.md`, `docs/vps-qualification.md` (SC-005).

## Dependencies and delivery strategy

Setup → foundation → stories in listed priority order → polish. The first story is the MVP; validate each story before adding the next. Shared files are edited sequentially. Existing implementations are verified rather than replaced. External tasks require an independent VPS and remain open until evidence is recorded.

## Independent work opportunities

After foundation, each story’s test review can be performed independently of other stories. Do not run two mutations of tools/protocols.py or tools/control.py concurrently. No task is marked [P] because the implementation tasks share state or files; read-only reviews of each story’s independent test are the parallel examples.
