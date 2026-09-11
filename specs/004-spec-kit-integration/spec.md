# Feature 004: Reproducible Spec Kit development workflow

Status: implementation in progress | Created: 2026-09-11

## Scope

Complete the repository's Spec Kit integration and maintainable development evidence. This feature does not deploy a production VPS or declare external acceptance complete. It preserves every pending external gate in features 001–003.

## User stories and acceptance scenarios

### US1 — Use the official workflow on either developer platform (P1)

Independent test: the official prerequisite helper resolves each feature on Ubuntu and Windows.

- **US1/AC1:** Given Python 3.12 on PATH and a checkout, when a developer follows docs/spec-kit.md, then pinned Specify CLI 1.0.6 and the checked-in Codex skills resolve the selected feature without an absolute machine path or Windows-only interpreter command.

### US2 — Understand and trace the existing product (P1)

Independent test: the repository audit resolves every FR, SC and acceptance scenario to tasks, source files and verification references.

- **US2/AC1:** Given any of features 001–003, when a maintainer opens the feature directory, then prioritized stories, measurable criteria, phased tasks, decisions, data ownership, interface contracts and a quickstart describe current implemented behavior and identify superseded history.
- **US2/AC2:** Given a pending external acceptance criterion, when the evidence is reviewed, then it has an unchecked task and an external verification reference rather than a claimed successful CI result.

### US3 — Detect stale artifacts before integration (P1)

Independent test: mutation fixtures make the audit fail for lost requirements, dangling evidence, broken task/story references and modified generated tooling.

- **US3/AC1:** Given a proposed change, when CI runs the structural audit and contract tests, then inconsistent traceability or contract drift fails with the affected file/ID; the tool explicitly does not claim to perform the agent's semantic analysis or convergence.

## Requirements

- FR-401: Pin Specify CLI 1.0.6 for development and retain the official Codex skills, scripts, templates and integration manifests without modifying upstream instructions.
- FR-402: Checked-in workflow commands must run with Python on PATH on Ubuntu and Windows; active feature context remains checkout-local and ignored by Git.
- FR-403: Features 001–004 have prioritized US IDs, acceptance IDs, measurable SC IDs, unique T IDs, phased tasks, research, data models, applicable contracts and quickstarts; preserve historical evidence and external tasks.
- FR-404: Document the cabinet HTTP and Unix control boundaries, allowed operations, input constraints, responses and error behavior; test contracts against actual handlers/validation.
- FR-405: A standard-library audit validates full FR/SC/AC traceability, task/story references, referenced files/test symbols, generated-file integrity and pending external gates.
- FR-406: CI runs the audit, official context helpers on Windows/Ubuntu and adversarial regression tests; failures are not ignored. Existing VPN/browser tests remain enabled.
- FR-407: Document actual agent tasks/analyze/implement/converge outcomes, the local ten-point rubric and the separate unperformed VPS acceptance; never present an internal score as official certification.

## Success criteria

- SC-401: Four feature directories resolve successfully with the official prerequisite helper on both CI platforms.
- SC-402: The structural audit reports zero errors and covers every declared FR/SC/AC with at least one valid task, implementation reference and verification reference.
- SC-403: The negative audit fixtures and actual interface contract tests pass; each intentionally malformed fixture is rejected.
- SC-404: The assessment links verifiable CI and agent-review evidence and retains all three unchecked external acceptance gates; no production deployment is claimed.

## Edge cases and entities

Duplicate IDs, unknown stories/tasks, missing paths or tests, edited upstream assets, Windows line endings and accidentally completed external tasks must be diagnosed. TraceabilityRow and GeneratedManifest are defined in data-model.md. Out of scope: CI invoking an LLM, paid external services, protocol redesign or merging/deploying PR #1.
