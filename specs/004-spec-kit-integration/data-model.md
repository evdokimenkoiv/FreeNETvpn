# Data model and invariants

TraceabilityRow: ref (FR/SC/USn/ACn within its feature), tasks (nonempty T IDs), implementation (nonempty repository-relative files), verification (nonempty file or file::PythonSymbol references), status (automated or external). External rows require an unchecked task and docs/acceptance.md. IDs are feature-scoped; file references cannot escape the repository.

GeneratedManifest: official .specify/integrations/*.manifest.json maps generated file paths to SHA256 digests. Compare normalized LF text so Git checkout line endings do not cause false corruption errors. Version is 1.0.6 in requirements and integration state. ActiveFeature is .specify/feature.json, ignored and never committed. The audit is read-only and makes no assertion that referenced tests passed merely because they exist.
