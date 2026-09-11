#!/usr/bin/env python3
"""Configuration, profiles and offline backups. Python standard library only."""
import argparse
import getpass
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {"wireguard", "vless", "ikev2", "l2tp", "outline", "amnezia"}
PORT_DEFAULTS = {"AWG_PORT": "51830", "OUTLINE_PORT": "2443", "OUTLINE_API_PORT": "19090"}
KEYS = {"CONFIG_VERSION", "DOMAIN", "WG_DOMAIN", "LE_EMAIL", "ADMIN_USER", "ADMIN_PASSWORD_HASH",
        "WG_PORT", "DNS1", "DNS2", "COMPOSE_PROFILES", "VLESS_UUID", "VLESS_WS_PATH", *PORT_DEFAULTS}


def parse_env(text):
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, raw = line.partition("=")
        key = key.strip()
        if not sep or key not in KEYS or key in values:
            raise ValueError(f"Invalid/duplicate configuration key on line {number}")
        parts = shlex.split(raw, comments=True, posix=True)
        if len(parts) > 1:
            raise ValueError(f"Quote values with spaces: {key}")
        values[key] = parts[0] if parts else ""
    return values


def validate(config):
    config = {**PORT_DEFAULTS, **config}
    if config.get("CONFIG_VERSION") != "2":
        raise ValueError("Legacy configuration: follow docs/migration.md; existing files were not overwritten")
    missing = KEYS - config.keys()
    if missing:
        raise ValueError("Missing keys: " + ", ".join(sorted(missing)))
    domain_re = r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"
    for key in ("DOMAIN", "WG_DOMAIN"):
        if not re.fullmatch(domain_re, config[key]):
            raise ValueError(f"{key} must be a lowercase DNS name, without scheme/path")
    if config["DOMAIN"] == config["WG_DOMAIN"]:
        raise ValueError("WireGuard UI needs its own hostname (WG_DOMAIN)")
    if not re.fullmatch(r"[A-Za-z0-9.!+_-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}", config["LE_EMAIL"]):
        raise ValueError("Invalid LE_EMAIL")
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,64}", config["ADMIN_USER"]):
        raise ValueError("ADMIN_USER must contain 5-64 letters, digits, underscores or hyphens")
    if not re.fullmatch(r"pbkdf2_sha256:600000:[0-9a-f]{32}:[0-9a-f]{64}", config["ADMIN_PASSWORD_HASH"]):
        raise ValueError("Invalid admin password hash; run configure")
    if not config["WG_PORT"].isdigit() or not 1024 <= int(config["WG_PORT"]) <= 65535:
        raise ValueError("WG_PORT must be between 1024 and 65535")
    profiles = config["COMPOSE_PROFILES"].split(",")
    if not profiles or any(p not in SUPPORTED for p in profiles) or len(profiles) != len(set(profiles)):
        raise ValueError("Supported profiles: " + ",".join(sorted(SUPPORTED)))
    for key in PORT_DEFAULTS:
        if not config[key].isdigit() or not 1024 <= int(config[key]) <= 65535:
            raise ValueError(f"{key} must be between 1024 and 65535")
    if len({int(config[k]) for k in ("WG_PORT", *PORT_DEFAULTS)}) != 4:
        raise ValueError("VPN and management ports must be distinct")
    for key in ("DNS1", "DNS2"):
        ipaddress.IPv4Address(config[key])
    if str(uuid.UUID(config["VLESS_UUID"])) != config["VLESS_UUID"]:
        raise ValueError("VLESS_UUID must be a canonical UUID")
    path = config["VLESS_WS_PATH"]
    if not re.fullmatch(r"/[a-zA-Z0-9_-]{8,100}", path) or path in {"/admin", "/healthz", "/auth", "/docs"}:
        raise ValueError("VLESS_WS_PATH must be a unique path with 8-100 safe characters")
    return config


def read_config(root=ROOT):
    return validate(parse_env((root / ".env").read_text(encoding="utf-8")))


def atomic_write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".new-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_config(config, root=ROOT):
    validate(config)
    atomic_write(root / ".env", "".join(f"{k}={shlex.quote(v)}\n" for k, v in config.items()))


def password_hash(password):
    if len(password) < 16 or len(password) > 1024:
        raise ValueError("Use an admin password of 16-1024 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000).hex()
    return f"pbkdf2_sha256:600000:{salt.hex()}:{digest}"


def configure(args, root=ROOT):
    if (root / ".env").exists():
        config = read_config(root)
        for argument, key in (("domain", "DOMAIN"), ("wg_domain", "WG_DOMAIN"), ("email", "LE_EMAIL")):
            if getattr(args, argument, None) not in (None, config[key]):
                raise ValueError("Existing configuration differs; edit .env deliberately, then run render")
        print("Existing configuration and credentials preserved")
    else:
        domain = args.domain or input("VPN domain (vpn.example.com): ").strip().lower()
        wg_domain = args.wg_domain or input("WireGuard UI domain (wg.example.com): ").strip().lower()
        email = args.email or input("Certificate email: ").strip()
        password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass("Admin password (16+ characters): ")
        config = dict(CONFIG_VERSION="2", DOMAIN=domain, WG_DOMAIN=wg_domain, LE_EMAIL=email,
                      ADMIN_USER=args.admin_user, ADMIN_PASSWORD_HASH=password_hash(password),
                      WG_PORT=str(args.wg_port), DNS1="1.1.1.1", DNS2="8.8.8.8", COMPOSE_PROFILES=args.services,
                      VLESS_UUID=str(uuid.uuid4()), VLESS_WS_PATH="/assets-" + secrets.token_hex(12))
        write_config(config, root)
    render(config, root)


def render(config, root=ROOT):
    config = validate(config)
    runtime = root / "runtime"
    runtime.mkdir(exist_ok=True)
    os.chmod(runtime, 0o700)
    (root / "data").mkdir(exist_ok=True)
    backups = root / "backups"
    backups.mkdir(exist_ok=True)
    os.chmod(backups, 0o750)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        os.chown(backups, 0, 10001)
    services = config["COMPOSE_PROFILES"].split(",")
    admin = dict(username=config["ADMIN_USER"], password_hash=config["ADMIN_PASSWORD_HASH"],
                 wg_domain=config["WG_DOMAIN"], services=services)
    atomic_write(runtime / "admin.json", json.dumps(admin, indent=2) + "\n", 0o644)
    xray = {"log": {"loglevel": "warning"}, "inbounds": [{"listen": "0.0.0.0", "port": 10000,
            "protocol": "vless", "settings": {"clients": [{"id": config["VLESS_UUID"]}], "decryption": "none"},
            "streamSettings": {"network": "ws", "wsSettings": {"path": config["VLESS_WS_PATH"]}}}],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}]}
    atomic_write(runtime / "xray.json", json.dumps(xray, indent=2) + "\n", 0o644)
    caddy = f"{{\n  email {config['LE_EMAIL']}\n}}\n\n{config['DOMAIN']} {{\n"
    caddy += '  @admin path /admin /admin/*\n  handle @admin {\n    reverse_proxy admin:8000\n  }\n'
    if "vless" in services:
        caddy += f"  @vless path {config['VLESS_WS_PATH']}\n  handle @vless {{\n    reverse_proxy xray:10000\n  }}\n"
    caddy += "  handle /healthz {\n    reverse_proxy admin:8000\n  }\n  handle {\n    root * /srv/site\n    file_server\n  }\n}\n"
    if "wireguard" in services:
        caddy += f"\n{config['WG_DOMAIN']} {{\n  forward_auth admin:8000 {{\n    uri /auth\n  }}\n  reverse_proxy wg-easy:51821\n}}\n"
    atomic_write(runtime / "Caddyfile", caddy, 0o644)
    from protocols import render as render_protocols
    render_protocols(config, root)
    print("Validated runtime configuration rendered")


def client_uri(config):
    validate(config)
    if "vless" not in config["COMPOSE_PROFILES"].split(","):
        raise ValueError("VLESS is not enabled")
    query = urlencode(dict(encryption="none", security="tls", sni=config["DOMAIN"],
                           type="ws", host=config["DOMAIN"], path=config["VLESS_WS_PATH"]))
    return f"vless://{config['VLESS_UUID']}@{config['DOMAIN']}:443?{query}#FreeNETvpn"


def compose(args, root=ROOT, capture=False, check=True):
    config = read_config(root)
    env = os.environ.copy()
    env.update(config)
    return subprocess.run(["docker", "compose", "--project-directory", str(root), "-p", "freenetvpn",
                           "--env-file", str(root / ".env"), "-f", str(root / "docker-compose.yml"), *args],
                          cwd=root, env=env, text=True, capture_output=capture, check=check)


def make_backup(root=ROOT):
    read_config(root)
    running = compose(["ps", "--status", "running", "--services"], root, capture=True).stdout.split()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = root / "backups" / f"freenetvpn-{stamp}.tar.gz"
    destination.parent.mkdir(exist_ok=True)
    temporary = destination.with_suffix(".partial")
    try:
        if running:
            compose(["stop", *running], root)
        with tarfile.open(temporary, "w:gz", dereference=False) as archive:
            for name in (".env", "runtime", "data"):
                path = root / name
                if path.exists():
                    archive.add(path, arcname=name)
        os.chmod(temporary, 0o640)
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            os.chown(temporary, 0, 10001)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
        if running:
            compose(["start", *running], root)
    print(destination)
    return destination


def checked_members(archive):
    members = archive.getmembers()
    seen = set()
    if sum(m.size for m in members) > 20 * 1024**3:
        raise ValueError("Backup exceeds the 20 GiB extraction limit")
    for member in members:
        path = PurePosixPath(member.name)
        if (not path.parts or path.is_absolute() or ".." in path.parts or "\\" in member.name
                or ":" in member.name or path.parts[0] not in {".env", "runtime", "data"}
                or not (member.isfile() or member.isdir()) or member.name in seen):
            raise ValueError(f"Unsafe archive entry: {member.name}")
        seen.add(member.name)
    if ".env" not in seen:
        raise ValueError("Backup has no .env")
    stream = archive.extractfile(".env")
    if stream is None:
        raise ValueError("Backup .env is not a file")
    config = validate(parse_env(stream.read(65537).decode("utf-8")))
    return members, config


def rotate_vless(root=ROOT):
    previous = read_config(root)
    if "vless" not in previous["COMPOSE_PROFILES"].split(","):
        raise ValueError("VLESS is not enabled")
    make_backup(root)
    updated = dict(previous, VLESS_UUID=str(uuid.uuid4()), VLESS_WS_PATH="/assets-" + secrets.token_hex(12))
    try:
        write_config(updated, root)
        render(updated, root)
        compose(["run", "--rm", "--no-deps", "xray", "run", "-test", "-config", "/etc/xray/config.json"], root)
        compose(["run", "--rm", "--no-deps", "caddy", "caddy", "validate", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"], root)
        compose(["up", "-d", "--force-recreate", "--wait", "caddy", "xray"], root)
    except Exception:
        write_config(previous, root)
        render(previous, root)
        compose(["up", "-d", "--force-recreate", "--wait", "caddy", "xray"], root)
        raise
    print("VLESS rotated. Replace profiles on all clients using tools/manage.py vless-uri")


def restore(archive_path, root=ROOT):
    # Refuse replacement rather than guessing which installation may be destroyed.
    for name in (".env", "runtime", "data"):
        path = root / name
        if path.is_symlink() or (path.exists() and (path.is_file() or any(path.iterdir()))):
            raise ValueError("Restore requires an empty installation (.env/runtime/data absent or empty)")
    with tarfile.open(archive_path, "r:gz") as archive:
        members, config = checked_members(archive)
        # Extract into a private staging directory only after validating every member.
        with tempfile.TemporaryDirectory(prefix=".restore-", dir=root) as staging:
            stage = Path(staging)
            for member in members:
                target = stage.joinpath(*PurePosixPath(member.name).parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    os.chmod(target, member.mode & 0o777)
                    if hasattr(os, "geteuid") and os.geteuid() == 0:
                        os.chown(target, member.uid, member.gid)
            for name in (".env", "runtime", "data"):
                if (stage / name).exists():
                    target = root / name
                    if target.is_dir():
                        target.rmdir()  # verified empty above
                    os.replace(stage / name, target)
    os.chmod(root / ".env", 0o600)
    render(config, root)
    print("Backup restored. Review DNS, then run sudo bash install.sh --existing")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    init = subs.add_parser("configure")
    for option in ("domain", "wg-domain", "email"):
        init.add_argument("--" + option)
    init.add_argument("--admin-user", default="admin")
    init.add_argument("--wg-port", type=int, default=51820)
    init.add_argument("--services", default="wireguard,vless,ikev2,l2tp,outline,amnezia")
    init.add_argument("--password-stdin", action="store_true")
    for command in ("validate", "render", "vless-uri", "backup", "rotate-vless"):
        subs.add_parser(command)
    get = subs.add_parser("get")
    get.add_argument("key", choices=sorted(KEYS - {"ADMIN_PASSWORD_HASH", "VLESS_UUID"}))
    comp = subs.add_parser("compose")
    comp.add_argument("args", nargs=argparse.REMAINDER)
    rest = subs.add_parser("restore")
    rest.add_argument("archive", type=Path)
    subs.add_parser("prepare-protocols")
    subs.add_parser("check-protocols")
    service_parser = subs.add_parser("services")
    service_parser.add_argument("selection", help="Comma-separated protocols, or all")
    client = subs.add_parser("client")
    client.add_argument("action", choices=["add", "list", "export", "revoke"])
    client.add_argument("protocol", choices=["ikev2", "l2tp", "outline", "amnezia"])
    client.add_argument("name", nargs="?")
    args = parser.parse_args()
    try:
        if args.command == "configure":
            configure(args)
        elif args.command in {"prepare-protocols", "check-protocols", "client", "services"}:
            import protocols
            if args.command == "prepare-protocols":
                protocols.prepare(read_config(), ROOT)
            elif args.command == "check-protocols":
                protocols.check(read_config(), ROOT)
            elif args.command == "services":
                updated = dict(read_config(), COMPOSE_PROFILES=",".join(sorted(SUPPORTED)) if args.selection == "all" else args.selection)
                validate(updated)
                make_backup()
                write_config(updated)
                render(updated)
                print("Selection saved; run sudo bash install.sh --existing")
            else:
                protocols.client(args.action, args.protocol, args.name, ROOT)
        elif args.command == "restore":
            restore(args.archive.resolve())
        elif args.command == "backup":
            make_backup()
        elif args.command == "rotate-vless":
            rotate_vless()
        elif args.command == "compose":
            compose(args.args)
        else:
            config = read_config()
            if args.command == "render":
                render(config)
            elif args.command == "get":
                print(config[args.key])
            elif args.command == "vless-uri":
                print(client_uri(config))
            else:
                print("Configuration OK")
    except (ValueError, OSError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
