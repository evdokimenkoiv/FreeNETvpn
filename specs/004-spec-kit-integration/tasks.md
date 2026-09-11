# Tasks: 004-spec-kit-integration

Generated using the official Spec Kit 1.0.6 task workflow and resolved template. Historical numbering/evidence for features 001–003 is retained in implementation-history.md. Completion below is based on verified current code; external acceptance stays open.

## Phase 1: Setup

- [x] T001 Pin official Specify CLI 1.0.6 and preserve generated upstream skills/manifests in `requirements-speckit.txt`, `.specify/integration.json`, `.specify/integrations/codex.manifest.json` (FR-401).

## Phase 2: Foundational

- [x] T002 Write adversarial audit fixtures and actual handler contract tests before implementing the new audit in `tests/test_spec_audit.py`, `tests/test_contracts.py` (FR-405 FR-406 SC-403).

## Phase 3: US1

Goal: deliver US1 as declared in spec.md (P1). Independent validation: `tests/test_spec_audit.py`.

- [x] T003 [US1] Select a validated feature portably and document Python PATH/UTF-8 setup in `tools/spec_context.py`, `docs/spec-kit.md`, `.specify/.gitignore` (FR-402 US1/AC1).

- [ ] T004 [US1] Run official prerequisite and task-template helpers for all four features on Windows and Ubuntu in `.github/workflows/ci.yml` (FR-401 FR-406 SC-401 US1/AC1).

## Phase 4: US2

Goal: deliver US2 as declared in spec.md (P1). Independent validation: `tools/spec_audit.py`.

- [x] T005 [US2] Normalize all four artifact sets, preserve history and create complete requirement/task/code/test references in `specs/traceability.json`, `specs/001-reliable-core/spec.md`, `specs/002-all-protocols/spec.md`, `specs/003-dashboard-presets/spec.md`, `specs/004-spec-kit-integration/spec.md` (FR-403 SC-402 US2/AC1).

- [x] T006 [US2] Publish HTTP/agent contracts and verify actual input, status, authentication and operation boundaries in `specs/003-dashboard-presets/contracts/http.json`, `specs/003-dashboard-presets/contracts/README.md` (FR-404 SC-403 US2/AC1).

- [x] T007 [US2] Preserve external gate rows with unchecked acceptance tasks in `specs/traceability.json`, `docs/acceptance.md` (FR-407 SC-404 US2/AC2).

## Phase 5: US3

Goal: deliver US3 as declared in spec.md (P1). Independent validation: `tests/test_spec_audit.py`.

- [x] T008 [US3] Implement a read-only stdlib audit with actionable errors and negative fixture coverage in `tools/spec_audit.py` (FR-405 SC-402 US3/AC1).

- [ ] T009 [US3] Make CI fail on structural/contract drift while retaining VPN and browser checks in `.github/workflows/ci.yml` (FR-406 SC-403 US3/AC1).

## Phase 6: Polish

- [ ] T010 Record actual agent analysis/implementation/convergence and publish the bounded ten-point assessment in `docs/spec-kit-assessment.md`, `docs/spec-kit-review.md` (FR-407 SC-404).

## Dependencies and delivery strategy

Setup → foundation → stories in listed priority order → polish. The first story is the MVP; validate each story before adding the next. Shared files are edited sequentially. Existing implementations are verified rather than replaced. External tasks require an independent VPS and remain open until evidence is recorded.

## Independent work opportunities

After foundation, each story’s test review can be performed independently of other stories. Do not run two mutations of tools/protocols.py or tools/control.py concurrently. No task is marked [P] because the implementation tasks share state or files; read-only reviews of each story’s independent test are the parallel examples.
