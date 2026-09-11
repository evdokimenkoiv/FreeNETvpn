"""Mutation tests: a green audit must not hide broken or fabricated evidence."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from spec_audit import audit


@pytest.fixture
def checkout(tmp_path):
    target = tmp_path / "checkout"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".pytest_cache", "runtime", "data", "backups", "node_modules"))
    return target


def test_repository_artifacts_are_consistent():
    result = audit(ROOT)
    assert result["ok"], result["errors"]
    assert result["features"] == 4
    assert result["requirements"] > 50


@pytest.mark.parametrize("mutation,needle", [
    ("missing_row", "FR-001"), ("unknown_task", "T999"),
    ("missing_test", "test_does_not_exist"), ("escaping_path", "outside"),
    ("duplicate_id", "duplicate"), ("unknown_story", "US99"),
    ("malformed_task", "malformed task"), ("external_done", "external"),
    ("external_relabel", "external"), ("missing_artifact", "research.md"),
    ("tampered_skill", "digest"), ("version_drift", "version"),
    ("broken_json", "traceability.json"), ("missing_feature", "001-reliable-core"),
])
def test_rejects_broken_or_false_evidence(checkout, mutation, needle):
    path = checkout / "specs/traceability.json"
    trace = json.loads(path.read_text(encoding="utf-8"))
    rows = trace["features"]["001-reliable-core"]
    taskfile = checkout / "specs/001-reliable-core/tasks.md"
    if mutation == "missing_row":
        rows[:] = [r for r in rows if r["ref"] != "FR-001"]
    elif mutation == "unknown_task":
        rows[0]["tasks"] = ["T999"]
    elif mutation == "missing_test":
        rows[0]["verification"] = ["tests/test_regressions.py::test_does_not_exist"]
    elif mutation == "escaping_path":
        rows[0]["implementation"] = ["../outside.py"]
    elif mutation == "duplicate_id":
        taskfile.write_text(taskfile.read_text(encoding="utf-8") + '\n- [x] T001 Duplicate in `tools/manage.py`.\n', encoding="utf-8")
    elif mutation == "unknown_story":
        taskfile.write_text(taskfile.read_text(encoding="utf-8").replace("[US1]", "[US99]"), encoding="utf-8")
    elif mutation == "malformed_task":
        taskfile.write_text(taskfile.read_text(encoding="utf-8").replace("T001 ", ""), encoding="utf-8")
    elif mutation == "external_done":
        taskfile.write_text(taskfile.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
    elif mutation == "external_relabel":
        next(r for r in rows if r["ref"] == "SC-005")["status"] = "automated"
    elif mutation == "missing_artifact":
        (checkout / "specs/001-reliable-core/research.md").unlink()
    elif mutation == "tampered_skill":
        skill = checkout / ".agents/skills/speckit-analyze/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nAltered upstream instruction.\n", encoding="utf-8")
    elif mutation == "version_drift":
        (checkout / "requirements-speckit.txt").write_text("specify-cli==0.0.1\n", encoding="utf-8")
    elif mutation == "missing_feature":
        shutil.rmtree(checkout / "specs/001-reliable-core")
    path.write_text("{broken" if mutation == "broken_json" else json.dumps(trace), encoding="utf-8")
    result = audit(checkout)
    assert not result["ok"]
    assert needle in " ".join(result["errors"]), result


def test_cli_failure_is_json_nonzero_and_read_only(checkout):
    path = checkout / "specs/traceability.json"
    path.write_text("{}", encoding="utf-8")
    before = {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, str(ROOT / "tools/spec_audit.py"), "--root", str(checkout), "--json"], capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)["ok"] is False
    assert before == {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()}


def test_context_rejects_traversal_and_preserves_existing_pointer(checkout):
    pointer = checkout / ".specify/feature.json"
    pointer.write_text('{"feature_directory":"specs/001-reliable-core"}', encoding="utf-8")
    before = pointer.read_bytes()
    for name in ["../outside", "missing", "specs/001-reliable-core"]:
        result = subprocess.run([sys.executable, str(checkout / "tools/spec_context.py"), name], capture_output=True)
        assert result.returncode != 0
        assert pointer.read_bytes() == before
    subprocess.run([sys.executable, str(checkout / "tools/spec_context.py"), "003-dashboard-presets"], check=True, capture_output=True)
    assert json.loads(pointer.read_text())["feature_directory"] == "specs/003-dashboard-presets"
