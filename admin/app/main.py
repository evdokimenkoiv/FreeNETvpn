"""Read-only control panel. No Docker socket, shell execution or host mounts."""
import hashlib
import hmac
import html
import json
import os
import re
import socket
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()
CONFIG = Path(os.getenv("ADMIN_CONFIG", "/run/freenet/admin.json"))
BACKUPS = Path(os.getenv("BACKUPS_DIR", "/srv/backups"))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, digest = encoded.split(":")
        iterations = int(rounds)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


@asynccontextmanager
async def lifespan(application):
    config = json.loads(CONFIG.read_text())
    if not config.get("username") or not config.get("password_hash"):
        raise RuntimeError("Run tools/manage.py configure before starting the panel")
    application.state.config = config
    yield


app = FastAPI(title="FreeNETvpn", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


def authenticated(credentials: HTTPBasicCredentials = Depends(security)):
    config = app.state.config
    # Evaluate both checks, including for a wrong username.
    username_ok = hmac.compare_digest(credentials.username.encode(), config["username"].encode())
    password_ok = verify_password(credentials.password, config["password_hash"])
    if not (username_ok and password_ok):
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": 'Basic realm="FreeNETvpn"'})
    return config


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/auth")
def auth_check(config=Depends(authenticated)):
    return {"authenticated": True}


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
def index(config=Depends(authenticated)):
    wg = html.escape(config["wg_domain"], quote=True)
    wg_link = f'<li><a href="https://{wg}/">WireGuard — клиенты и QR-коды</a></li>' if "wireguard" in config["services"] else ""
    vless_help = '<p>Профиль VLESS: <code>sudo bash menu.sh</code> на сервере.</p>' if "vless" in config["services"] else ""
    enabled = html.escape(", ".join(config["services"]))
    return f"""<!doctype html><html lang="ru"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width"><title>FreeNETvpn</title>
    <style>body{{font:18px system-ui;max-width:760px;margin:6vh auto;padding:24px;background:#101827;color:#edf3ff}}
    a{{color:#88d9ff}}li{{margin:18px 0}}code{{background:#22314a;padding:4px}}</style>
    <h1>FreeNETvpn</h1><p>Управление вашим VPN-сервером</p><ul>
    {wg_link}
    <li><a href="/admin/status">Доступность сервисов</a></li>
    <li><a href="/admin/backups">Готовые резервные копии</a></li></ul>
    {vless_help}
    <p>Включённые протоколы: {enabled}.</p>
    <p>Клиенты IKEv2, L2TP, Outline и AmneziaWG: <code>sudo bash menu.sh</code>, пункт 7.</p>
    <p>Создание полной резервной копии: <code>sudo bash scripts/backup.sh</code>.</p>
    <p>Статус TCP-портов не подтверждает прохождение VPN-трафика.</p></html>"""


@app.get("/admin/status")
def status(config=Depends(authenticated)):
    targets = {}
    for service, host, port in [("wireguard", "wg-easy", 51821), ("vless", "xray", 10000)]:
        if service not in config["services"]:
            continue
        try:
            with socket.create_connection((host, port), timeout=2):
                targets[service] = "tcp reachable"
        except OSError:
            targets[service] = "unreachable"
    for service in ("ikev2", "l2tp", "amnezia", "outline"):
        if service in config["services"]:
            targets[service] = "enabled; check on server with scripts/health_check.sh"
    return {"checks": targets, "scope": "Configuration and selected TCP reachability only; test a VPN client separately"}


@app.get("/admin/backups")
def backups(config=Depends(authenticated)):
    return {"backups": sorted(p.name for p in BACKUPS.glob("freenetvpn-*.tar.gz") if p.is_file() and not p.is_symlink()),
            "create": "sudo bash scripts/backup.sh"}


@app.get("/admin/backup")
def latest_backup(config=Depends(authenticated)):
    candidates = sorted(p for p in BACKUPS.glob("freenetvpn-*.tar.gz") if p.is_file() and not p.is_symlink())
    if not candidates:
        raise HTTPException(404, "No backups yet; run sudo bash scripts/backup.sh on the server")
    return FileResponse(candidates[-1], filename=candidates[-1].name, media_type="application/gzip",
                        headers={"Cache-Control": "no-store"})


@app.get("/admin/backups/{filename}")
def download_backup(filename: str, config=Depends(authenticated)):
    if not re.fullmatch(r"freenetvpn-[A-Za-z0-9_-]+\.tar\.gz", filename):
        raise HTTPException(404, "Backup not found")
    path = BACKUPS / filename
    if not path.is_file() or path.is_symlink():
        raise HTTPException(404, "Backup not found")
    return FileResponse(path, filename=filename, media_type="application/gzip",
                        headers={"Cache-Control": "no-store"})
