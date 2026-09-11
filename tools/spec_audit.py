#!/usr/bin/env python3
"""Read-only structural SDD audit. Does not perform LLM analysis or run VPN tests."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

VERSION = "1.0.6"
TASK = re.compile(r"^- \[([ xX])\] (T\d{3,}) (?:\[P\] )?(?:\[(US\d+)\] )?(.+)$")
DECLARATION = re.compile(r"^- ((?:FR|SC)-\d{3}):.*$", re.M)
AC = re.compile(r"\*\*(US\d+/AC\d+):\*\*")
STORY = re.compile(r"^### (US\d+) .+\(P[123]\)", re.M)


def audit(root):
    root = Path(root).resolve()
    errors = []
    total = 0

    def problem(where, message):
        errors.append(f"{where}: {message}")

    def path_for(relative):
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ValueError(f"invalid repository path {relative!r}")
        path = (root / relative).resolve()
        if Path(relative).is_absolute() or not path.is_relative_to(root):
            raise ValueError(f"path outside repository: {relative}")
        return path

    def read(relative):
        try:
            return path_for(relative).read_text(encoding="utf-8")
        except (OSError, ValueError) as exc:
            problem(relative, str(exc))
            return ""

    def read_json(relative):
        try:
            data = json.loads(read(relative))
            if not isinstance(data, dict):
                raise ValueError("expected JSON object")
            return data
        except (ValueError, TypeError) as exc:
            problem(relative, str(exc))
            return {}

    def reference(value, where):
        try:
            if not isinstance(value, str):
                raise ValueError("reference must be a string")
            relative, sep, symbol = value.partition("::")
            path = path_for(relative)
            if not path.is_file():
                raise ValueError(f"missing file {value}")
            if sep:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
                if symbol not in names:
                    raise ValueError(f"missing Python symbol {value}")
        except (OSError, ValueError, SyntaxError) as exc:
            problem(where, str(exc))

    trace = read_json("specs/traceability.json")
    if trace.get("schema_version") != 1:
        problem("specs/traceability.json", "schema_version must be 1")
    features = trace.get("features", {})
    if not isinstance(features, dict):
        problem("specs/traceability.json", "features must be an object")
        features = {}
    actual = {p.name for p in (root / "specs").glob("[0-9][0-9][0-9]-*") if p.is_dir()}
    if not actual:
        problem("specs/", "no feature directories")
    for name in sorted(actual ^ set(features)):
        problem(name, "feature directory and traceability inventory disagree")

    for name in sorted(actual):
        prefix = f"specs/{name}"
        texts = {file: read(f"{prefix}/{file}") for file in
                 ("spec.md", "plan.md", "tasks.md", "research.md", "data-model.md", "quickstart.md")}
        for file, content in texts.items():
            if not content.strip():
                problem(f"{prefix}/{file}", "empty or missing artifact")
        if not any((root / prefix / "contracts").glob("*")):
            problem(prefix, "missing contracts")
        declared = DECLARATION.findall(texts["spec.md"]) + AC.findall(texts["spec.md"])
        requirements = set(declared)
        total += len(requirements)
        for ident, count in Counter(declared).items():
            if count > 1:
                problem(prefix, f"duplicate requirement {ident}")
        stories = STORY.findall(texts["spec.md"])
        if not stories or len(stories) != len(set(stories)):
            problem(prefix, "missing or duplicate prioritized user stories")
        for story in stories:
            if not any(ref.startswith(story + "/AC") for ref in requirements):
                problem(prefix, f"{story} has no acceptance scenario")
        external = {m.group(1) for m in DECLARATION.finditer(texts["spec.md"]) if "External gate:" in m.group(0)}
        tasks = {}
        for line in texts["tasks.md"].splitlines():
            if not line.startswith("- ["):
                continue
            match = TASK.fullmatch(line)
            if not match:
                problem(prefix, f"malformed task: {line}")
                continue
            mark, ident, story, description = match.groups()
            if ident in tasks:
                problem(prefix, f"duplicate task {ident}")
            if story and story not in stories:
                problem(prefix, f"{ident} unknown story {story}")
            paths = re.findall(r"`([^`]+)`", description)
            if not paths:
                problem(prefix, f"{ident} has no explicit file path")
            for value in paths:
                reference(value, f"{prefix}/{ident}")
            tasks[ident] = (mark.lower() == "x", story)
        if not tasks or "## Phase 1: Setup" not in texts["tasks.md"] or "## Phase 2: Foundational" not in texts["tasks.md"]:
            problem(prefix, "missing phased tasks")
        rows = features.get(name, [])
        if not isinstance(rows, list):
            problem(prefix, "traceability rows must be an array")
            rows = []
        seen = set()
        mapped_tasks = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("ref"), str):
                problem(prefix, "invalid traceability row")
                continue
            ref = row["ref"]
            where = f"{prefix}/{ref}"
            if ref in seen:
                problem(where, "duplicate traceability row")
            seen.add(ref)
            if ref not in requirements:
                problem(where, "unknown requirement")
            ids = row.get("tasks")
            if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
                problem(where, "tasks must be a nonempty ID array")
                ids = []
            for ident in ids:
                if ident not in tasks:
                    problem(where, f"unknown task {ident}")
                mapped_tasks.add(ident)
            if ref.startswith("US"):
                story = ref.split("/")[0]
                if story not in stories or not any(tasks.get(ident, (False, None))[1] == story for ident in ids):
                    problem(where, "acceptance scenario lacks a task in its own story")
            for key in ("implementation", "verification"):
                values = row.get(key)
                if not isinstance(values, list) or not values:
                    problem(where, f"{key} must be a nonempty reference array")
                    continue
                for value in values:
                    reference(value, where)
            if row.get("status") not in {"automated", "external"}:
                problem(where, "invalid evidence status")
            if ref in external and row.get("status") != "external":
                problem(where, "external gate relabeled as automated")
            if row.get("status") == "external":
                if not any(ident in tasks and not tasks[ident][0] for ident in ids):
                    problem(where, "external gate must retain an unchecked task")
                if "docs/acceptance.md" not in row.get("verification", []):
                    problem(where, "external gate must reference docs/acceptance.md")
        for ref in sorted(requirements - seen):
            problem(prefix, f"unmapped requirement {ref}")
        for ident in sorted(set(tasks) - mapped_tasks):
            problem(prefix, f"unmapped task {ident}")

    integration = read_json(".specify/integration.json")
    if integration.get("version") != VERSION or f"specify-cli=={VERSION}" not in read("requirements-speckit.txt").splitlines():
        problem("Spec Kit", f"version must be pinned to {VERSION}")
    registered = set()
    for name in ("codex", "speckit"):
        manifest = read_json(f".specify/integrations/{name}.manifest.json")
        if manifest.get("version") != VERSION:
            problem(name, "manifest version drift")
        files = manifest.get("files", {})
        if not isinstance(files, dict) or not files:
            problem(name, "missing generated file inventory")
            continue
        for relative, expected in files.items():
            content = read(relative)
            registered.add(relative)
            # Upstream uses text digests; normalize CRLF checkouts to its LF generation.
            digest = hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()
            if digest != expected:
                problem(relative, "generated file digest mismatch; regenerate with pinned CLI")
            if relative.endswith("SKILL.md") and (".venv/Scripts/" in content or re.search(r"[A-Z]:[/\\]Users[/\\]", content)):
                problem(relative, "machine-specific interpreter path")
    for folder in (".agents/skills", ".specify/scripts", ".specify/templates"):
        for path in (root / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                if path.relative_to(root).as_posix() not in registered:
                    problem(path.relative_to(root), "unregistered generated file")
    if "feature.json" not in read(".specify/.gitignore").splitlines():
        problem(".specify/.gitignore", "active feature pointer must be ignored")
    return {"ok": not errors, "features": len(actual), "requirements": total, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit(args.root)
    if args.json:
        print(json.dumps(result, ensure_ascii=True))
    else:
        print(f"{'PASS' if result['ok'] else 'FAIL'}: {result['features']} features, {result['requirements']} requirement/acceptance references")
        for error in result["errors"]:
            print(error)
        print("Structural validation only; semantic review and successful test runs require separate evidence.")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
