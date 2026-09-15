# Implementation plan

Use the official Spec Kit 1.0.6 Codex skills and Python scripts. Add a stdlib audit and platform-independent feature selector; test invalid artifact fixtures and actual cabinet/agent contracts. Preserve runtime code and the deployment command.

## Technical context and project structure

Python 3.12 for development/CI; stdlib management and Spec Kit helper scripts; FastAPI admin with pinned dependencies; Docker Compose and systemd on Ubuntu 22.04/24.04/26.04 x86_64 for runtime. Ubuntu 26.04 host qualification is recorded separately in docs/vps-qualification.md; the packet CI matrix remains 22.04/24.04. Windows supports development checks, not the VPN server runtime. Sources live in tools/, admin/, services/ and scripts/; tests/ contains regression, browser and Linux traffic suites. No runtime dependency on Specify CLI.

## Design artifacts

- research.md records decisions and rejected alternatives.
- data-model.md defines ownership, secret boundaries and invariants.
- contracts/ defines this feature's external interface; 003 owns the cabinet/agent contract.
- quickstart.md gives the repeatable validation path.

## Phases and constitution check

Setup establishes artifact/dependency inputs; foundation validates ownership/security; each prioritized story is implemented and independently verified; final cross-cutting checks preserve historical evidence and external acceptance. tasks.md lists exact source/test paths and dependencies. All six constitution principles apply: reproducible checks; preserve existing secrets/data; authenticated administration without arbitrary commands; validate configuration as data; failing CI; secret-free Git and explicit external limitations. No exception is requested.

Feature touch-points: requirements-speckit.txt, tools/spec_context.py, tools/spec_audit.py, tests/test_spec_audit.py, tests/test_contracts.py, specs/traceability.json, .github/workflows/ci.yml, docs/spec-kit.md and docs/spec-kit-assessment.md. Existing .specify/memory/constitution.md is preserved.
