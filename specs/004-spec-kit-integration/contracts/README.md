# Structural audit CLI contract

Run python tools/spec_audit.py [--root PATH] [--json]. Default root is the source checkout. Standard-library only, no network or mutation. Exit 0 means structural validation passed; exit 1 means validation errors. JSON output: {ok:boolean, features:integer, requirements:integer, errors:[string]}. Every error names a path or feature/ID; malformed JSON/files must produce an error rather than silently skip the feature. This is not the LLM analyze/converge workflow and does not verify packet traffic or public deployment.

Traceability input is specs/traceability.json with schema_version=1 and features mapping feature directory names to rows described in data-model.md. The audit rejects missing/duplicate rows, dangling tasks/files/test symbols, story mismatches, malformed task lines, missing supported artifacts, upstream file/hash/version mismatch and externally scoped rows with all tasks marked complete.
