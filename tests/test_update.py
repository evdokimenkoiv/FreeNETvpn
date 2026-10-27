"""Filesystem transaction tests with Docker/network fault injection."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import update as updater
import diagnostics
import manage

SHA = "a" * 40


def archive(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for name, value in entries.items():
            entry = tarfile.TarInfo("release/" + name)
            if value is None:
                entry.type = tarfile.SYMTYPE
                entry.linkname = "/etc/passwd"
                tar.addfile(entry)
            else:
                value = value.encode()
                entry.size = len(value)
                tar.addfile(entry, io.BytesIO(value))


@pytest.fixture
def installation(tmp_path, monkeypatch):
    root = tmp_path / "vpn"
    root.mkdir()
    (root / "tools").mkdir()
    (root / "tools/manage.py").write_text("old management code")
    (root / "install.sh").write_text("old installer")
    (root / "docker-compose.yml").write_text("old services")
    (root / ".env").write_bytes(b"SECRET unchanged settings")
    (root / "data/control").mkdir(parents=True)
    (root / "data/control/accounts.json").write_text('{"owner":"same-password-hash"}')
    (root / "runtime").mkdir()
    (root / "runtime/config").write_text("old runtime")
    (root / "backups").mkdir()
    (root / "backups/keep").write_text("previous backup")
    (root / ".updates").mkdir()
    calls = []
    def fetch(url, target=None):
        if target is None:
            return {"sha": SHA}
        archive(target, {"install.sh": "new installer", "tools/manage.py": "new management code",
                         "docker-compose.yml": "new services", "new-file.txt": "new file"})
    def command(root, *args, **kwargs):
        calls.append(tuple(args))
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(updater, "fetch", fetch)
    monkeypatch.setattr(updater, "manage", command)
    monkeypatch.setattr(updater, "compose", command)
    monkeypatch.setattr(updater, "run", command)
    monkeypatch.setattr(updater, "stop_writers", lambda root: {"agent_active": True, "running": ["admin", "caddy"]})
    monkeypatch.setattr(updater.shutil, "disk_usage", lambda root: type("Disk", (), {"free": 100 * 1024**3})())
    monkeypatch.setenv("FREENET_LANG", "en")
    return root, calls


def test_update_preserves_users_settings_backups_and_pins_revision(installation):
    root, calls = installation
    before = (root / ".env").read_bytes(), (root / "data/control/accounts.json").read_bytes()
    updater.update(root, "main")
    assert before == ((root / ".env").read_bytes(), (root / "data/control/accounts.json").read_bytes())
    assert (root / "backups/keep").read_text() == "previous backup"
    assert (root / "install.sh").read_text() == "new installer"
    assert json.loads((root / "data/release.json").read_text())["commit"] == SHA
    txn = next(p.parent for p in (root / ".updates").glob("*/transaction.json"))
    with tarfile.open(txn / "state.tar.gz") as tar:
        assert tar.extractfile("data/control/accounts.json").read() == before[1]
        assert tar.extractfile(".env").read() == before[0]
    assert (txn / "old-code/install.sh").read_text() == "old installer"
    assert not (root / ".updates/pending.json").exists()
    assert ("bash", str(root / "install.sh"), "--existing", "--no-firewall") in calls


def test_failed_apply_resumes_saved_revision_without_replacing_new_users(installation, monkeypatch):
    root, calls = installation
    def fail(root, *args, **kwargs):
        if args[0] == "bash":
            raise subprocess.CalledProcessError(19, ["install"])
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(updater, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        updater.update(root, "main")
    pending = json.loads((root / ".updates/pending.json").read_text())
    txn = root / ".updates" / pending["transaction"]
    snapshot = (txn / "state.tar.gz").read_bytes()
    (root / "data/control/accounts.json").write_text('{"owner":"same","new-user":"preserve"}')
    monkeypatch.setattr(updater, "fetch", lambda *a: pytest.fail("must resume pinned local revision"))
    monkeypatch.setattr(updater, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0))
    updater.update(root, "different-ref")
    assert "new-user" in (root / "data/control/accounts.json").read_text()
    assert snapshot == (txn / "state.tar.gz").read_bytes()
    assert not (root / ".updates/pending.json").exists()


def test_backup_failure_resumes_old_services_before_any_code_change(installation, monkeypatch):
    root, calls = installation
    monkeypatch.setattr(updater, "snapshot_state", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        updater.update(root, "main")
    assert (root / "install.sh").read_text() == "old installer"
    assert ("start", "admin", "caddy") in calls
    assert ("systemctl", "start", "freenetvpn-control") in calls


def test_download_failure_does_not_stop_services_or_change_state(installation, monkeypatch):
    root, calls = installation
    monkeypatch.setattr(updater, "fetch", lambda *a: (_ for _ in ()).throw(OSError("network")))
    with pytest.raises(OSError):
        updater.update(root, "main")
    assert calls == [("validate",)]
    assert (root / "install.sh").read_text() == "old installer"
    assert not (root / ".updates/pending.json").exists()


def test_local_code_edits_are_not_overwritten(installation):
    root, calls = installation
    updater.update(root, "main")
    (root / "new-file.txt").write_text("operator customization")
    with pytest.raises(ValueError, match="changed locally"):
        updater.update(root, "main")
    assert (root / "new-file.txt").read_text() == "operator customization"


def test_rollback_requires_explicit_state_choice_and_keeps_newer_users(installation):
    root, calls = installation
    updater.update(root, "main")
    txn = next(p.parent for p in (root / ".updates").glob("*/transaction.json"))
    (root / "data/control/accounts.json").write_text('{"new-user":"recoverable"}')
    with pytest.raises(ValueError, match="--restore-state"):
        updater.rollback(root, txn, False)
    assert "new-user" in (root / "data/control/accounts.json").read_text()
    updater.rollback(root, txn, True)
    assert (root / "install.sh").read_text() == "old installer"
    assert not (root / "new-file.txt").exists()
    assert "owner" in (root / "data/control/accounts.json").read_text()
    rescue = next(txn.glob("rescue-*"))
    assert "new-user" in (rescue / "data/control/accounts.json").read_text()
    assert (root / "backups/keep").exists()


@pytest.mark.parametrize("name,value", [("../escape", "x"), (".env", "overwrite"), ("data/users", "x"), ("backups/file", "x"), (".git/config", "x"), ("link", None)])
def test_release_cannot_overwrite_state_or_escape(tmp_path, name, value):
    path = tmp_path / "release.tar.gz"
    archive(path, {name: value})
    with pytest.raises(ValueError):
        updater.extract_code(path, tmp_path / "stage")
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("message,code", [("no such host", "IMAGE_DNS"), ("no space left on device", "IMAGE_DISK"),
    ("x509: certificate", "IMAGE_TLS"), ("toomanyrequests", "IMAGE_LIMIT"), ("manifest unknown", "IMAGE_NOT_FOUND"),
    ("unauthorized", "IMAGE_AUTH"), ("unknown flag: --ignore-buildable", "COMPOSE_VERSION"),
    ("context deadline exceeded", "IMAGE_NETWORK"), ("unrecognized failure", "IMAGE_PULL")])
def test_pull_diagnostics_explain_registry_failures(tmp_path, capsys, monkeypatch, message, code):
    monkeypatch.setenv("FREENET_LANG", "en")
    (tmp_path / ".env").write_text("private")
    diagnostics.image_pull_failure(message, tmp_path)
    text = capsys.readouterr().err
    assert code in text and "--existing" in text and "compose pull --ignore-buildable" in text


def test_compose_uses_real_env_path_and_propagates_pull_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(manage, "read_config", lambda root: {})
    def run(argv, **kwargs):
        assert argv[argv.index("--env-file") + 1] == str(tmp_path / ".env")
        return subprocess.CompletedProcess(argv, 1, "", "manifest unknown: image unavailable")
    monkeypatch.setattr(manage.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        manage.compose(["pull", "--ignore-buildable"], tmp_path)
    assert "IMAGE_NOT_FOUND" in capsys.readouterr().err


@pytest.mark.parametrize("free,inodes,expected", [(1024**3, 50000, 1), (20 * 1024**3, 20, 1), (20 * 1024**3, 50000, 0)])
def test_storage_checks_bytes_and_inodes_separately(tmp_path, monkeypatch, capsys, free, inodes, expected):
    from types import SimpleNamespace
    monkeypatch.setattr(diagnostics.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, str(tmp_path)))
    monkeypatch.setattr(diagnostics.os, "statvfs", lambda p: SimpleNamespace(f_bavail=free, f_frsize=1, f_favail=inodes, f_files=100000), raising=False)
    assert diagnostics.storage(tmp_path) == expected
    output = capsys.readouterr()
    assert ("IMAGE_DISK" in output.err) == bool(expected)


def test_interrupted_code_copy_can_resume_without_importing_mixed_code(installation, monkeypatch):
    root, calls = installation
    original = updater.atomic_copy
    count = 0
    def interrupted(source, destination):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("interrupted file copy")
        original(source, destination)
    monkeypatch.setattr(updater, "atomic_copy", interrupted)
    with pytest.raises(OSError):
        updater.update(root, "main")
    monkeypatch.setattr(updater, "atomic_copy", original)
    monkeypatch.setattr(updater, "manage", lambda *a, **kw: pytest.fail("mixed-version management code imported"))
    updater.update(root, "main")
    assert (root / "tools/manage.py").read_text() == "new management code"
    assert not (root / ".updates/pending.json").exists()


def test_concurrent_updater_is_refused_before_mutation(installation, monkeypatch):
    fcntl = pytest.importorskip("fcntl")
    root, calls = installation
    monkeypatch.setattr(updater.os, "geteuid", lambda: 0)
    monkeypatch.setattr(updater.os, "umask", lambda value: 0o077)
    monkeypatch.setattr(sys, "argv", ["update.py", "--root", str(root)])
    monkeypatch.setattr(updater, "update", lambda *a: pytest.fail("second updater ran"))
    with (root / ".updates/lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert updater.main() == 1
    assert not (root / ".updates/updater.py").exists()


def test_backup_disk_failure_explains_cause_without_exposing_paths():
    import errno
    message = updater.failure_message(OSError(errno.ENOSPC, "No space left", "/private/SECRET"))
    assert "df -h" in message and "inodes" in message and "SECRET" not in message
