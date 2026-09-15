import base64
import json
import subprocess
import uuid
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from test_regressions import panel, config, deployment, PASSWORD
from test_protocols import extra
import manage
import protocols
import presets
from control import Controller


@pytest.fixture
def browser(deployment, monkeypatch):
    monkeypatch.setattr(panel, "CONFIG", deployment / "runtime/admin.json")
    with TestClient(panel.app, base_url="https://vpn.example.test") as client:
        yield client


def login(browser):
    result = browser.post("/admin/api/login", json={"username": "admin", "password": PASSWORD}, headers={"Origin": "https://vpn.example.test"})
    assert result.status_code == 200
    assert all(value in result.headers["set-cookie"] for value in ("HttpOnly", "Secure", "SameSite=strict", "Path=/admin"))
    return {"Origin": "https://vpn.example.test", "X-CSRF-Token": result.json()["csrf"]}


@pytest.mark.parametrize("path", ["session", "overview", "export?protocol=vless&name=legacy", "qr?protocol=vless&name=legacy"])
def test_dashboard_data_is_private(browser, path):
    response = browser.get("/admin/api/" + path)
    assert response.status_code == 401
    assert "www-authenticate" not in response.headers
    assert "Basic" in browser.get("/auth").headers["www-authenticate"]


def test_session_csrf_logout_and_secret_exclusion(browser, monkeypatch):
    assert browser.post("/admin/api/login", json={"username": "admin", "password": PASSWORD}, headers={"Origin": "https://evil.test"}).status_code == 403
    headers = login(browser)
    session = browser.get("/admin/api/session").json()
    assert session["csrf"] == headers["X-CSRF-Token"]
    assert "control_token" not in session and "password_hash" not in session
    calls = []
    monkeypatch.setattr(panel, "control", lambda method, data: calls.append((method, data)) or {"id": "test"})
    body = {"operation": "backup.create"}
    assert browser.post("/admin/api/jobs", json=body).status_code == 403
    assert browser.post("/admin/api/jobs", json=body, headers={**headers, "Origin": "https://evil.test"}).status_code == 403
    assert not calls
    assert browser.post("/admin/api/jobs", json=body, headers=headers).status_code == 202
    assert calls == [("submit", body)]
    assert browser.post("/admin/api/logout", headers=headers).status_code == 200
    assert browser.get("/admin/api/session").status_code == 401


def test_expired_session_and_login_rate_limit(browser):
    login(browser)
    for value in panel.app.state.sessions.values():
        value["expires"] = 0
    assert browser.get("/admin/api/session").status_code == 401
    for _ in range(11):
        assert browser.post("/admin/api/login", json={"username": "admin", "password": "wrong"}, headers={"Origin": "https://vpn.example.test"}).status_code == 401
    assert browser.post("/admin/api/login", json={"username": "admin", "password": PASSWORD}, headers={"Origin": "https://vpn.example.test"}).status_code == 429


def test_csp_assets_and_qr_remain_local(browser, monkeypatch):
    response = browser.get("/admin")
    assert response.status_code == 401 and "login-form" in response.text
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert browser.get("/admin/assets/app.js").status_code == 200
    login(browser)
    monkeypatch.setattr(panel, "control", lambda *args: {"content": base64.b64encode(b"vless://test@vpn.example.test:443").decode()})
    response = browser.get("/admin/api/qr?protocol=vless&name=test")
    assert response.status_code == 200 and "<svg" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert browser.get("/admin/api/qr?protocol=ikev2&name=test").status_code == 400


@pytest.mark.parametrize("payload", [
    {"operation": "exec", "command": "id"},
    {"operation": "service.restart", "protocol": "xray;id"},
    {"operation": "client.add", "protocol": "vless", "name": "../escape"},
    {"operation": "client.add", "protocol": "vless", "name": "ok", "preset": "reality"},
    {"operation": "client.revoke", "protocol": "vless", "name": "legacy"},
    {"operation": "service.start", "protocol": "amnezia"},
    {"operation": "client.preset", "protocol": "wireguard", "name": "ok", "preset": "mobile"},
])
def test_agent_rejects_unsupported_requests(deployment, payload):
    controller = Controller(deployment, worker=False)
    with pytest.raises(ValueError):
        controller.submit(dict(payload, request_id=str(uuid.uuid4())))
    assert not controller.jobs


def test_queue_idempotency_and_no_persisted_password(deployment):
    controller = Controller(deployment, worker=False)
    request = dict(operation="wireguard.connect", protocol="wireguard", username="admin", password="secret-for-native-wg", request_id=str(uuid.uuid4()))
    first = controller.submit(request)
    assert controller.submit(request) == first and controller.queue.qsize() == 1
    assert "secret-for-native-wg" not in controller.path.read_text()
    assert Controller(deployment, worker=False).jobs[0]["status"] == "interrupted"


def test_service_allowlist_and_snapshot_redaction(deployment, monkeypatch):
    calls = []
    def compose(args, root, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, '[{"Service":"xray","State":"running","Health":"healthy"}]', '')
    monkeypatch.setattr(manage, "compose", compose)
    controller = Controller(deployment, worker=False)
    controller.execute(dict(operation="service.restart", protocol="vless"))
    assert calls == [["restart", "xray"]]
    snapshot = controller.snapshot()
    assert next(s for s in snapshot["services"] if s["id"] == "vless")["state"] == "running"
    assert "VLESS_UUID" not in json.dumps(snapshot) and "control_token" not in json.dumps(snapshot)


def test_wireguard_poll_and_job_serialize_native_sqlite_sessions(deployment, monkeypatch):
    import concurrent.futures
    import time
    (deployment / "tools").mkdir()
    (deployment / "tools/wg_bridge.js").write_text("// fixed test adapter")
    active = 0
    maximum = 0
    def compose(args, root, **kwargs):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        time.sleep(0.05)
        active -= 1
        return subprocess.CompletedProcess(args, 0, "[]", "")
    monkeypatch.setattr(manage, "compose", compose)
    controller = Controller(deployment, worker=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(controller.wg_api, "list", credentials={"username": "admin", "password": "test"}) for _ in range(2)]
        assert [future.result() for future in futures] == [[], []]
    assert maximum == 1


@pytest.mark.parametrize("preset", ["ws-tls", "mobile-ws", "grpc-tls"])
def test_vless_presets_lifecycle_and_legacy_survives(deployment, monkeypatch, preset):
    monkeypatch.setattr(manage, "compose", lambda *a, **k: None)
    original = manage.read_config(deployment)["VLESS_UUID"]
    protocols.client("add", "vless", "phone", deployment, preset=preset)
    peer = protocols.read_state(deployment)["clients"]["vless"]["phone"]
    controller = Controller(deployment, worker=False)
    exported = controller.export("vless", "phone")
    query = parse_qs(urlsplit(base64.b64decode(exported["content"]).decode()).query)
    assert query["security"] == ["tls"]
    assert query["type"] == [presets.get("vless", preset)["transport"]]
    document = json.loads(base64.b64decode(controller.export("vless", "phone", "json")["content"]))
    assert document["outbounds"][0]["streamSettings"]["tlsSettings"]["allowInsecure"] is False
    protocols.client("preset", "vless", "phone", deployment, preset="grpc-tls")
    assert protocols.read_state(deployment)["clients"]["vless"]["phone"]["uuid"] == peer["uuid"]
    protocols.client("revoke", "vless", "phone", deployment)
    assert peer["uuid"] not in (deployment / "runtime/xray.json").read_text()
    assert original in (deployment / "runtime/xray.json").read_text()
    with pytest.raises(ValueError):
        controller.export("vless", "phone")


def test_vless_failed_validation_rolls_back(deployment, monkeypatch):
    calls = []
    def compose(args, root):
        calls.append(args)
        if args[0] == "run":
            raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(manage, "compose", compose)
    before = (deployment / "runtime/xray.json").read_bytes()
    with pytest.raises(subprocess.CalledProcessError):
        protocols.client("add", "vless", "phone", deployment)
    assert not protocols.read_state(deployment)["clients"]["vless"]
    assert (deployment / "runtime/xray.json").read_bytes() == before
    assert calls[-1][-1] == "xray"


@pytest.mark.parametrize("preset", ["balanced", "mobile", "economy"])
def test_amnezia_templates_keep_identity_and_server_headers(extra, monkeypatch, preset):
    root, config = extra
    monkeypatch.setattr(manage, "compose", lambda *a, **k: None)
    monkeypatch.setattr(protocols, "keypair", lambda: {"private": "C"*43+"=", "public": "D"*43+"="})
    protocols.client("add", "amnezia", "phone", root)
    before = protocols.read_state(root)
    server_before = (root / "runtime/amnezia/awg0.conf").read_bytes()
    protocols.client("preset", "amnezia", "phone", root, preset=preset)
    after = protocols.read_state(root)
    assert before["awg"] == after["awg"]
    assert before["clients"]["amnezia"]["phone"]["private"] == after["clients"]["amnezia"]["phone"]["private"]
    assert (root / "runtime/amnezia/awg0.conf").read_bytes() == server_before
    exported = protocols.export_client("amnezia", "phone", config, after, root).read_text()
    profile = presets.get("amnezia", preset)
    assert f'MTU = {profile["mtu"]}' in exported
    assert f'PersistentKeepalive = {profile["keepalive"]}' in exported
    for key, value in before["awg"]["params"].items():
        if key.startswith(("S", "H")):
            assert f"{key} = {value}" in exported
