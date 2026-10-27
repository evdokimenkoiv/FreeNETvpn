#!/usr/bin/env python3
"""Pinned, backed-up updates of an existing FreeNETvpn installation (stdlib only)."""
import argparse
import errno
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import urllib.error

REPO = "https://api.github.com/repos/evdokimenkoiv/FreeNETvpn"
STATE = {".env", "data", "runtime"}
PROTECTED = STATE | {"backups", ".updates", ".git", ".venv", "node_modules", "__pycache__"}
MAX_CODE = 256 * 1024**2


def localize(en, ru):
    return ru if os.environ.get("FREENET_LANG", os.environ.get("LANG", "en")).lower().startswith("ru") else en


def say(en, ru):
    print(localize(en, ru), flush=True)


def failure_message(error):
    if isinstance(error, subprocess.CalledProcessError):
        return localize(f"command exit {error.returncode}; inspect the specific error above", f"команда завершилась с кодом {error.returncode}; конкретная причина указана выше")
    if isinstance(error, BlockingIOError):
        return localize("Another updater holds the lock; wait for it to finish. Do not delete the lock file.", "Уже работает другое обновление; дождитесь завершения. Не удаляйте файл блокировки.")
    if isinstance(error, urllib.error.HTTPError):
        return localize(f"GitHub HTTP {error.code}; check selected revision, connectivity and API rate limits, then retry.", f"GitHub HTTP {error.code}; проверьте выбранную версию, сеть и лимит API, затем повторите.")
    if isinstance(error, urllib.error.URLError):
        return localize("GitHub connection/DNS/TLS failed; check server connectivity and retry.", "Ошибка соединения/DNS/TLS GitHub; проверьте сеть сервера и повторите.")
    if isinstance(error, OSError) and error.errno in {errno.ENOSPC, errno.EDQUOT}:
        return localize("No disk space/inodes/quota for the update or backup. Check df -h and df -i; enlarge storage or free cache, preserving VPN state.", "Нет места/inode/квоты для обновления или копии. Проверьте df -h и df -i; увеличьте диск или очистите кэш, сохраняя данные VPN.")
    if isinstance(error, OSError):
        return f"OS error {error.errno}: {error.strerror or 'check permissions and filesystem availability'}"
    if isinstance(error, KeyboardInterrupt):
        return localize("Interrupted; retained transaction can be resumed.", "Прервано; сохранённое обновление можно продолжить.")
    return str(error)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".new")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def safe_path(root, name, state=False):
    path = PurePosixPath(name)
    if (not path.parts or path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name
            or (state and path.parts[0] not in STATE)
            or (not state and path.parts[0] in PROTECTED)):
        raise ValueError("Unsafe/protected archive path")
    result = root.joinpath(*path.parts)
    for part in [result, *result.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError("Symlink in installation path; inspect it before updating")
    return result


def fetch(url, target=None):
    request = urllib.request.Request(url, headers={"User-Agent": "FreeNETvpn-updater", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        if target is None:
            return json.loads(response.read(1024 * 1024))
        with target.open("wb") as stream:
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > MAX_CODE:
                    raise ValueError("Release archive exceeds download limit")
                stream.write(block)


def extract_code(archive, destination):
    files, seen, total, prefix = [], set(), 0, None
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            parts = PurePosixPath(member.name).parts
            if not parts or not (member.isfile() or member.isdir()):
                raise ValueError("Release contains links or special files")
            prefix = prefix or parts[0]
            if parts[0] != prefix:
                raise ValueError("Release has multiple roots")
            if len(parts) == 1:
                if not member.isdir():
                    raise ValueError("Invalid release root")
                continue
            name = "/".join(parts[1:])
            path = safe_path(destination, name)
            if name in seen:
                raise ValueError("Duplicate release path")
            seen.add(name)
            total += member.size
            if total > MAX_CODE or len(seen) > 20000:
                raise ValueError("Release exceeds extraction limit")
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, path.open("wb") as output:
                    shutil.copyfileobj(source, output)
                os.chmod(path, 0o755 if member.mode & 0o111 else 0o644)
                files.append(name)
    for required in ("install.sh", "tools/manage.py", "docker-compose.yml"):
        if required not in files:
            raise ValueError("Incomplete release archive")
    return sorted(files)


def run(root, *args, capture=False, check=True):
    return subprocess.run(args, cwd=root, text=True, capture_output=capture, check=check)


def manage(root, *args, **kwargs):
    return run(root, sys.executable, str(root / "tools/manage.py"), *args, **kwargs)


def compose(root, *args, **kwargs):
    # Independent of project Python imports, including recovery from interrupted file copies.
    return run(root, "docker", "compose", "--project-directory", str(root), "-p", "freenetvpn",
               "--env-file", str(root / ".env"), "-f", str(root / "docker-compose.yml"), *args, **kwargs)


def atomic_copy(source, destination):
    missing = []
    parent = destination.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for parent in reversed(missing):
        parent.mkdir()
        # Code assets must remain traversable by non-root service containers.
        # Existing private directories (.updates) are never broadened.
        os.chmod(parent, 0o755)
    fd, temporary = tempfile.mkstemp(prefix=".update-", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def code_hashes(root, names):
    return {name: hashlib.sha256(safe_path(root, name).read_bytes()).hexdigest() for name in names}


def snapshot_state(root, destination):
    temporary = destination.with_suffix(".partial")
    try:
        with tarfile.open(temporary, "w:gz", dereference=False) as archive:
            for name in sorted(STATE):
                path = safe_path(root, name, state=True)
                if path.exists():
                    for child in [path, *path.rglob("*")] if path.is_dir() else [path]:
                        if child.is_symlink() or not (child.is_file() or child.is_dir()):
                            raise ValueError("State contains a link/special file; backup requires manual review")
                    archive.add(path, arcname=name)
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def restore_state(root, archive_path):
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        seen = set()
        for member in members:
            safe_path(root, member.name, state=True)
            if member.name in seen or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe state backup")
            seen.add(member.name)
        if ".env" not in seen:
            raise ValueError("State backup has no .env")
        # Only locally-created regular files/directories in the three state roots.
        archive.extractall(root, members=members)


def stop_writers(root):
    active = run(root, "systemctl", "is-active", "--quiet", "freenetvpn-control", check=False).returncode == 0
    running = compose(root, "ps", "--status", "running", "--services", capture=True).stdout.split()
    return {"agent_active": active, "running": running}


def stop(root, previous):
    if previous["agent_active"]:
        run(root, "systemctl", "stop", "freenetvpn-control")
    if previous["running"]:
        compose(root, "stop", *previous["running"])


def restart_previous(root, previous):
    if previous["running"]:
        compose(root, "start", *previous["running"])
    if previous["agent_active"]:
        run(root, "systemctl", "start", "freenetvpn-control")


def save_old_code(root, txn, names):
    old = {}
    for name in names:
        path = safe_path(root, name)
        if path.exists() and not path.is_file():
            raise ValueError("Release file conflicts with an existing directory")
        old[name] = path.exists()
        if old[name]:
            destination = txn / "old-code" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    return old


def apply_code(root, txn, record, rollback=False):
    names = record["old_files"] if rollback else record["files"]
    for name in names:
        destination = safe_path(root, name)
        if rollback and not record["old_files"][name]:
            destination.unlink(missing_ok=True)
        else:
            atomic_copy(txn / ("old-code" if rollback else "candidate") / name, destination)
    if not rollback:
        for name in record["old_files"]:
            if name not in record["files"]:
                safe_path(root, name).unlink(missing_ok=True)


def apply_update(root, txn, record):
    metadata = txn / "transaction.json"
    if not record.get("backup_complete"):
        previous = record.get("previous") or stop_writers(root)
        record["previous"] = previous
        write_json(metadata, record)
        say("Pausing services for a consistent backup and update.", "Останавливаю сервисы для согласованной копии и обновления.")
        try:
            stop(root, previous)
            snapshot_state(root, txn / "state.tar.gz")
            old_manifest = root / ".updates/installed-files.json"
            names = set(record["files"])
            if old_manifest.exists():
                names.update(json.loads(old_manifest.read_text()))
            record["old_files"] = save_old_code(root, txn, sorted(names))
            record["backup_complete"] = True
            write_json(metadata, record)
        except BaseException:
            restart_previous(root, previous)
            raise
    record["phase"] = "applying"
    write_json(metadata, record)
    # A failed prior attempt may have started some services. Quiesce them on retry too.
    stop(root, stop_writers(root))
    apply_code(root, txn, record)
    # Reuse the existing installation contract; never invoke configure/reset/firewall edits.
    run(root, "bash", str(root / "install.sh"), "--existing", "--no-firewall")
    write_json(root / "data/release.json", {"commit": record["commit"], "updated_at": datetime.now(timezone.utc).isoformat()})
    write_json(root / ".updates/installed-files.json", record["files"])
    write_json(root / ".updates/installed-hashes.json", code_hashes(root, record["files"]))
    record["phase"] = "complete"
    write_json(metadata, record)
    (root / ".updates/pending.json").unlink(missing_ok=True)
    say(f"UPDATE OK: {record['commit']}. Backup: {txn}", f"ОБНОВЛЕНО: {record['commit']}. Резервная копия: {txn}")


def rollback(root, txn, restore):
    if not restore:
        raise ValueError("Rollback restores old users/settings too. Add --restore-state explicitly; current state will be retained in a rescue archive.")
    record = json.loads((txn / "transaction.json").read_text())
    if not record.get("backup_complete"):
        raise ValueError("This transaction has no complete rollback snapshot")
    pending = root / ".updates/pending.json"
    if pending.exists() and json.loads(pending.read_text())["transaction"] != txn.name:
        raise ValueError("Another update is pending; resolve it before rolling back this transaction")
    previous = stop_writers(root)
    rescue = txn / ("rescue-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    rescue.mkdir(mode=0o700)
    stop(root, previous)
    try:
        snapshot_state(root, rescue / "state.tar.gz")
        save_old_code(root, rescue, sorted(record["old_files"]))
        restored = rescue / "restored"
        restored.mkdir(mode=0o700)
        restore_state(restored, txn / "state.tar.gz")
    except BaseException:
        restart_previous(root, previous)
        raise
    # Rename current state instead of deleting it; all post-update users remain recoverable.
    for name in STATE:
        path = safe_path(root, name, state=True)
        if path.exists():
            path.rename(rescue / name)
        if (restored / name).exists():
            (restored / name).rename(path)
    apply_code(root, txn, record, rollback=True)
    run(root, "bash", str(root / "install.sh"), "--existing", "--no-firewall")
    write_json(root / ".updates/installed-files.json", [name for name, existed in record["old_files"].items() if existed])
    write_json(root / ".updates/installed-hashes.json", code_hashes(root, [name for name, existed in record["old_files"].items() if existed]))
    record["phase"] = "rolled_back"
    write_json(txn / "transaction.json", record)
    (root / ".updates/pending.json").unlink(missing_ok=True)
    say(f"ROLLBACK OK. Newer state retained at {rescue}", f"ОТКАТ ЗАВЕРШЁН. Более новые данные сохранены: {rescue}")


def update(root, ref):
    pending = root / ".updates/pending.json"
    if pending.exists():
        name = json.loads(pending.read_text())["transaction"]
        if not re.fullmatch(r"[0-9TZ-]+-[0-9a-f]{12}", name):
            raise ValueError("Invalid pending transaction")
        txn = root / ".updates" / name
        say(f"Resuming saved update: {name}", f"Продолжаю сохранённое обновление: {name}")
        return apply_update(root, txn, json.loads((txn / "transaction.json").read_text()))
    manage(root, "validate")
    installed_hashes = root / ".updates/installed-hashes.json"
    if installed_hashes.exists():
        hashes = json.loads(installed_hashes.read_text())
        if any(not safe_path(root, name).is_file() or code_hashes(root, [name])[name] != digest for name, digest in hashes.items()):
            raise ValueError("Managed project files were changed locally. Save/review changes before updating; settings in .env/data are unaffected.")
    elif (root / ".git").exists():
        dirty = run(root, "git", "status", "--porcelain", "--untracked-files=no", capture=True).stdout
        if dirty:
            raise ValueError("Tracked local changes detected. Save/review them before using the updater; do not reset settings.")
    commit = fetch(REPO + "/commits/" + urllib.parse.quote(ref, safe=""))["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid GitHub revision")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    txn = root / ".updates" / (stamp + "-" + commit[:12])
    txn.mkdir(mode=0o700)
    shutil.copy2(Path(__file__).resolve(), txn / "updater.py")
    fetch(REPO + "/tarball/" + commit, txn / "release.tar.gz")
    candidate = txn / "candidate"
    candidate.mkdir(mode=0o700)
    files = extract_code(txn / "release.tar.gz", candidate)
    # Validation runs against a private copy; active state remains untouched.
    shutil.copy2(root / ".env", candidate / ".env")
    manage(candidate, "validate")
    (candidate / ".env").unlink()
    state_size = sum(p.stat().st_size for name in STATE for p in (root / name).rglob("*") if p.is_file()) + (root / ".env").stat().st_size
    if shutil.disk_usage(root).free < 2 * state_size + MAX_CODE + 1024**3:
        raise ValueError("Insufficient free disk space for backup/update; free space without deleting VPN state")
    # Check path collisions before pausing anything.
    for name in files:
        path = safe_path(root, name)
        if path.exists() and not path.is_file():
            raise ValueError("Release path conflicts with a local directory")
    record = {"commit": commit, "files": files, "phase": "staged", "backup_complete": False}
    write_json(txn / "transaction.json", record)
    write_json(pending, {"transaction": txn.name})
    apply_update(root, txn, record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/opt/freenetvpn"))
    parser.add_argument("--ref", default="main")
    parser.add_argument("--rollback")
    parser.add_argument("--restore-state", action="store_true")
    args = parser.parse_args()
    root = args.root.absolute()
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        parser.error("Run on the Ubuntu server with sudo")
    if not re.fullmatch(r"/[a-zA-Z0-9_./-]+", str(root)) or root != root.resolve():
        parser.error("Use the real installation directory without spaces or symlinks")
    os.umask(0o077)
    if args.restore_state and not args.rollback:
        parser.error("--restore-state requires --rollback ID")
    if not (root / "tools/manage.py").is_file() or not (root / ".env").is_file():
        parser.error("Existing installation and .env required; run install.sh first")
    directory = root / ".updates"
    if directory.is_symlink() or (directory / "lock").is_symlink():
        parser.error("Unsafe update directory/lock")
    import fcntl
    try:
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
        with (directory / "lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if Path(__file__).resolve() != directory / "updater.py":
                atomic_copy(Path(__file__).resolve(), directory / "updater.py")
            if args.rollback:
                if not re.fullmatch(r"[0-9TZ-]+-[0-9a-f]{12}", args.rollback):
                    raise ValueError("Invalid rollback ID")
                rollback(root, directory / args.rollback, args.restore_state)
            else:
                update(root, args.ref)
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        # Never include subprocess argv or a configuration dump.
        detail = failure_message(error)
        say(f"ERROR [UPDATE_FAILED]: {detail}", f"ОШИБКА [UPDATE_FAILED]: {detail}")
        say("Snapshots and any rescue data remain under .updates. Fix the error above, then repeat the command below. A pending update resumes its saved revision; do not delete .env/data or snapshots.", "Копии и аварийно сохранённые данные остаются в .updates. Исправьте ошибку выше и повторите команду ниже. Обновление продолжит сохранённую версию; не удаляйте .env/data и копии.")
        if (directory / "updater.py").is_file():
            extra = " --rollback " + shlex.quote(args.rollback) + " --restore-state" if args.rollback else ""
            print("  sudo python3 " + shlex.quote(str(directory / "updater.py")) + " --root " + shlex.quote(str(root)) + extra)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
