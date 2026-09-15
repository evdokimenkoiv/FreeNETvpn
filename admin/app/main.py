"""Authenticated dashboard; fixed operations go to a restricted local agent."""
import base64
import hashlib
import hmac
import html
import json
import os
import re
import socket
import secrets
import time
import io
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict

security = HTTPBasic(auto_error=False)
CONFIG = Path(os.getenv("ADMIN_CONFIG", "/run/freenet/admin.json"))
BACKUPS = Path(os.getenv("BACKUPS_DIR", "/srv/backups"))
STATIC = Path(__file__).parent / "static"
CONTROL_SOCKET = os.getenv("CONTROL_SOCKET", "/run/freenet-control/control.sock")


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
    application.state.sessions = {}
    application.state.login_attempts = {}
    yield


app = FastAPI(title="FreeNETvpn", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/admin/assets", StaticFiles(directory=STATIC), name="assets")


@app.middleware("http")
async def security_headers(request, call_next):
    length = request.headers.get("content-length", "0")
    if not length.isdigit():
        return JSONResponse({"detail": "Invalid content length"}, status_code=400)
    if int(length) > 65536:
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    response = await call_next(request)
    response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"})
    return response


def authenticated(request: Request, credentials: HTTPBasicCredentials | None = Depends(security)):
    config = app.state.config
    # JSON API failures return the custom login screen, not a browser-native
    # Basic Auth popup. Preserve that challenge for wg-easy forward_auth/CLI.
    challenge = {} if request.url.path.startswith("/admin/api/") else {"WWW-Authenticate": 'Basic realm="FreeNETvpn"'}
    session = app.state.sessions.get(request.cookies.get("freenet_session", ""))
    if session and session["expires"] > time.time():
        user = account(session.get("username", config["username"]))
        if user and user["enabled"] and user["revision"] == session.get("revision", "owner"):
            request.state.auth_mode = "session"
            request.state.session = session
            return {**config, **user}
    if credentials is None:
        raise HTTPException(401, "Войдите в кабинет", headers=challenge)
    # Evaluate both checks, including for a wrong username.
    user = authenticate_account(credentials.username, credentials.password)
    if not user:
        raise HTTPException(401, "Invalid credentials", headers=challenge)
    request.state.auth_mode = "basic"
    return {**config, **user}


def account(username):
    config = app.state.config
    if username == config["username"]:
        return dict(username=username, display_name=username, role="admin", enabled=True,
                    locale="ru", grants=[], revision="owner", is_owner=True)
    return control("accounts", {"action": "get", "values": {"username": username}})


def authenticate_account(username, password):
    config = app.state.config
    if hmac.compare_digest(username.encode(), config["username"].encode()):
        return account(username) if verify_password(password, config["password_hash"]) else None
    try:
        return control("accounts", {"action": "authenticate", "values": {"username": username, "password": password}})
    except HTTPException as error:
        if error.status_code == 503:
            return None  # unavailable account storage must never grant access
        raise


def administrator(config=Depends(authenticated)):
    if config["role"] != "admin":
        raise HTTPException(403, "Administrator access required")
    return config




def same_origin(request):
    if request.headers.get("origin") != "https://" + app.state.config["domain"]:
        raise HTTPException(403, "Недопустимый источник запроса")


def mutation(request: Request, config=Depends(authenticated)):
    same_origin(request)
    if request.state.auth_mode == "session":
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), request.state.session["csrf"]):
            raise HTTPException(403, "Обновите страницу: проверка сессии не пройдена")
    elif request.headers.get("x-freenet-request") != "1":
        raise HTTPException(403, "Требуется защита от CSRF")
    return config


def admin_mutation(config=Depends(mutation)):
    if config["role"] != "admin":
        raise HTTPException(403, "Administrator access required")
    return config


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


@app.post("/admin/api/login")
def login(body: Login, request: Request, response: Response):
    same_origin(request)
    now = time.time()
    key = body.username.casefold()
    if len(app.state.login_attempts) > 2048:
        app.state.login_attempts = {k:v for k,v in app.state.login_attempts.items() if v and now-v[-1] < 60}
        if len(app.state.login_attempts) > 2048:
            raise HTTPException(429, "Try again later")
    attempts = [t for t in app.state.login_attempts.get(key, []) if now-t < 60]
    app.state.login_attempts[key] = attempts
    if len(attempts) >= 12:
        raise HTTPException(429, "Слишком много попыток. Повторите через минуту")
    attempts.append(now)
    config = app.state.config
    user = authenticate_account(body.username, body.password)
    if not user:
        raise HTTPException(401, "Неверный логин или пароль")
    app.state.sessions = {k:v for k,v in app.state.sessions.items() if v["expires"] > now}
    if len(app.state.sessions) >= 1000:
        raise HTTPException(429, "Слишком много активных сессий")
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    app.state.sessions[token] = {"csrf": csrf, "expires": now + 8*3600, "username": user["username"], "revision": user["revision"]}
    response.set_cookie("freenet_session", token, max_age=8*3600, secure=True, httponly=True, samesite="strict", path="/admin")
    return {**public_user(user), "csrf": csrf}


@app.get("/admin/api/session")
def session(request: Request, config=Depends(authenticated)):
    return {**public_user(config), "csrf": getattr(request.state, "session", {}).get("csrf"), "domain": config["domain"]}


@app.post("/admin/api/logout")
def logout(request: Request, response: Response, config=Depends(mutation)):
    app.state.sessions.pop(request.cookies.get("freenet_session", ""), None)
    response.delete_cookie("freenet_session", path="/admin", secure=True, httponly=True, samesite="strict")
    return {"ok": True}


def control(method, data=None):
    payload = json.dumps({"token": app.state.config["control_token"], "method": method, "data": data}).encode() + b"\n"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(35)
            connection.connect(CONTROL_SOCKET)
            connection.sendall(payload)
            with connection.makefile("rb") as stream:
                raw = stream.readline(2*1024*1024 + 1)
        if len(raw) > 2*1024*1024:
            raise ValueError("Response too large")
        result = json.loads(raw)
    except (OSError, ValueError):
        raise HTTPException(503, "Сервис управления недоступен. Проверьте freenetvpn-control на сервере.")
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result["data"]


@app.get("/admin/api/overview")
def overview(config=Depends(authenticated)):
    data = control("snapshot")
    if config["role"] == "admin":
        return data
    clients = [c for c in data["clients"] if permitted(config, c)]
    return {"domain": config["domain"], "clients": [{k:v for k,v in c.items() if k in {"protocol", "name", "preset", "address"}} for c in clients], "observed_at": data["observed_at"]}


@app.post("/admin/api/jobs", status_code=202)
def submit(body: dict, config=Depends(admin_mutation)):
    return control("submit", body)


@app.get("/admin/api/telemetry")
def telemetry(config=Depends(administrator)):
    return control("telemetry")


@app.get("/admin/api/maintenance")
def maintenance(config=Depends(administrator)):
    return control("maintenance")


@app.post("/admin/api/maintenance/preview")
def maintenance_preview(body: dict, config=Depends(admin_mutation)):
    return control("maintenance_preview", body)


@app.get("/admin/api/export")
def export(protocol: str, name: str, format: str = "default", config=Depends(authenticated)):
    return allowed_export(config, protocol, name, format)


@app.get("/admin/api/qr")
def qr(protocol: str, name: str, config=Depends(authenticated)):
    if protocol not in {"vless", "amnezia", "wireguard", "outline", "mtproto"}:
        raise HTTPException(400, "Для этого протокола используйте файл конфигурации")
    import qrcode
    import qrcode.image.svg
    exported = allowed_export(config, protocol, name)
    image = qrcode.make(base64.b64decode(exported["content"]).decode().strip(), image_factory=qrcode.image.svg.SvgPathImage, border=4)
    data = io.BytesIO()
    image.save(data)
    return Response(data.getvalue(), media_type="image/svg+xml")


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/auth")
def auth_check(config=Depends(administrator)):
    return {"authenticated": True}


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
def index(request: Request, credentials: HTTPBasicCredentials | None = Depends(security)):
    status = 200
    try:
        authenticated(request, credentials)
    except HTTPException:
        status = 401
    content = (STATIC / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content.replace("{{WG_DOMAIN}}", html.escape(app.state.config["wg_domain"], quote=True)), status_code=status)


@app.get("/admin/status")
def status(config=Depends(administrator)):
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
def backups(config=Depends(administrator)):
    return {"backups": sorted(p.name for p in BACKUPS.glob("freenetvpn-*.tar.gz") if p.is_file() and not p.is_symlink()),
            "create": "sudo bash scripts/backup.sh"}


@app.get("/admin/backup")
def latest_backup(config=Depends(administrator)):
    candidates = sorted(p for p in BACKUPS.glob("freenetvpn-*.tar.gz") if p.is_file() and not p.is_symlink())
    if not candidates:
        raise HTTPException(404, "No backups yet; run sudo bash scripts/backup.sh on the server")
    return FileResponse(candidates[-1], filename=candidates[-1].name, media_type="application/gzip",
                        headers={"Cache-Control": "no-store"})


@app.get("/admin/backups/{filename}")
def download_backup(filename: str, config=Depends(administrator)):
    if not re.fullmatch(r"freenetvpn-[A-Za-z0-9_-]+\.tar\.gz", filename):
        raise HTTPException(404, "Backup not found")
    path = BACKUPS / filename
    if not path.is_file() or path.is_symlink():
        raise HTTPException(404, "Backup not found")
    return FileResponse(path, filename=filename, media_type="application/gzip",
                        headers={"Cache-Control": "no-store"})


def public_user(user):
    return {k:user[k] for k in ("username", "display_name", "role", "locale", "is_owner")}


def permitted(user, client):
    return any(all(g.get(k) == client.get(k) for k in ("protocol", "name", "identity")) for g in user["grants"])


def allowed_export(user, protocol, name, format="default"):
    data = {"protocol": protocol, "name": name, "format": format}
    if user["role"] == "admin":
        return control("export", data)
    if not any(g["protocol"] == protocol and g["name"] == name for g in user["grants"]):
        raise HTTPException(403, "Profile access denied")
    return control("account_export", {**data, "username": user["username"]})


@app.get("/admin/api/users")
def users(config=Depends(administrator)):
    return control("accounts", {"action": "list", "values": {"actor": config["username"]}})


@app.post("/admin/api/users")
def save_user(body: dict, config=Depends(admin_mutation)):
    if "actor" in body:
        raise HTTPException(422, "Invalid account fields")
    return control("accounts", {"action": "save", "values": {**body, "actor": config["username"]}})


@app.delete("/admin/api/users/{username}")
def delete_user(username: str, config=Depends(admin_mutation)):
    return control("accounts", {"action": "delete", "values": {"actor": config["username"], "username": username}})


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=1024)
    password: str = Field(min_length=16, max_length=1024)


@app.post("/admin/api/password")
def change_password(body: PasswordChange, config=Depends(mutation)):
    return control("accounts", {"action": "password", "values": {**body.model_dump(), "actor": config["username"]}})
