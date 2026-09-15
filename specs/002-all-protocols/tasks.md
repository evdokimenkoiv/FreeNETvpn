# Tasks: 002-all-protocols

Generated using the official Spec Kit 1.0.6 task workflow and resolved template. Historical numbering/evidence for features 001–003 is retained in implementation-history.md. Completion below is based on verified current code; external acceptance stays open.

## Phase 1: Setup

- [x] T001 Record restoration decisions and protocol ownership in `specs/002-all-protocols/plan.md`, `specs/002-all-protocols/data-model.md` (FR-205).

## Phase 2: Foundational

- [x] T002 Preserve protocol secrets and validate configuration, names and ports in `tools/protocols.py`, `tools/manage.py` (FR-205).

## Phase 3: US1

Goal: deliver US1 as declared in spec.md (P1). Independent validation: `tests/integration_extra.py`.

- [x] T003 [US1] Implement certificate/EAP IKEv2 and protected PPP/L2TP with actual traffic checks in `services/ipsec/start.sh`, `tools/protocols.py` (FR-201 FR-202 SC-201 US1/AC1 US1/AC2).

## Phase 4: US2

Goal: deliver US2 as declared in spec.md (P1). Independent validation: `tests/integration_extra.py`.

- [x] T004 [US2] Implement local authenticated Outline key lifecycle and pinned AmneziaWG with restart/revoke checks in `tools/protocols.py`, `services/amnezia/Dockerfile`, `docker-compose.yml` (FR-203 FR-204 SC-202 US2/AC1).

## Phase 5: US3

Goal: deliver US3 as declared in spec.md (P1). Independent validation: `tests/test_protocols.py::test_protocol_secrets_survive_backup_restore`.

- [x] T005 [US3] Preserve v2 configuration, PKI and client secrets through preparation and backup/restore in `tools/protocols.py`, `tools/manage.py` (FR-205 SC-203 US3/AC1).

## Phase 6: Polish

- [x] T006 Keep all four restored protocol traffic checks on both Ubuntu baselines in `.github/workflows/ci.yml` (FR-206).

- [ ] T007 Record independent VPS ports/native applications/reboot/recovery acceptance (EXTERNAL — pending) in `docs/acceptance.md` (SC-204).

## Dependencies and delivery strategy

Setup → foundation → stories in listed priority order → polish. The first story is the MVP; validate each story before adding the next. Shared files are edited sequentially. Existing implementations are verified rather than replaced. External tasks require an independent VPS and remain open until evidence is recorded.

## Independent work opportunities

After foundation, each story’s test review can be performed independently of other stories. Do not run two mutations of tools/protocols.py or tools/control.py concurrently. No task is marked [P] because the implementation tasks share state or files; read-only reviews of each story’s independent test are the parallel examples.
