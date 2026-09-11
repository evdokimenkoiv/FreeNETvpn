# Validate 002-all-protocols

From the repository root, install development requirements with `python -m pip install -r requirements-dev.txt` and run `python -m pytest -q`.

Select this feature using `python tools/spec_context.py 002-all-protocols`; then `python .specify/scripts/python/check_prerequisites.py --json --require-spec --require-tasks --include-tasks` must resolve its spec, plan, tasks and supporting documents. Run `python tools/spec_audit.py` to validate cross-artifact references. Agent workflow and platform setup: docs/spec-kit.md.

Linux packet and Chromium commands are defined in .github/workflows/ci.yml. Run tests/integration.py and tests/integration_extra.py only on a disposable supported Linux host: they create privileged containers and test networking. The browser suite uses a simulated API and is not production telemetry. The first bash block in README.md is the installation command; docs/deployment.md lists DNS, platform and port prerequisites. Public DNS/CA/native-client/reboot/recovery acceptance follows docs/acceptance.md; it is still pending.
