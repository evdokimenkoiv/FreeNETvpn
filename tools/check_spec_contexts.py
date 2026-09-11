#!/usr/bin/env python3
"""Smoke-test official Spec Kit helpers; preserve the developer's active context."""
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    pointer = root / ".specify/feature.json"
    original = pointer.read_bytes() if pointer.exists() else None
    try:
        for feature in sorted((root / "specs").glob("[0-9][0-9][0-9]-*")):
            env = dict(os.environ, PYTHONUTF8="1", SPECIFY_FEATURE_DIRECTORY=str(feature), SPECIFY_INIT_DIR=str(root))
            for script, args in [
                ("check_prerequisites.py", ["--require-spec", "--require-tasks", "--include-tasks"]),
                ("setup_tasks.py", []),
            ]:
                result = subprocess.run([sys.executable, str(root / ".specify/scripts/python" / script), "--json", *args],
                                        cwd=root, env=env, check=True, capture_output=True, text=True, encoding="utf-8")
                data = json.loads(result.stdout)
                if Path(data["FEATURE_DIR"]).resolve() != feature.resolve():
                    raise ValueError(f"{script}: wrong feature context for {feature.name}")
                required = {"research.md", "data-model.md", "contracts/", "quickstart.md"}
                if not required.issubset(data["AVAILABLE_DOCS"]):
                    raise ValueError(f"{script}: missing design documents for {feature.name}")
                if script == "setup_tasks.py" and not data.get("TASKS_TEMPLATE_CONTENT"):
                    raise ValueError("Official tasks template was not resolved")
            print(f"PASS {feature.name}: official prerequisite and task-template helpers")
    finally:
        if original is None:
            pointer.unlink(missing_ok=True)
        else:
            pointer.write_bytes(original)


if __name__ == "__main__":
    main()
