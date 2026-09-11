"""Consumer contracts exercise real HTTP and Unix handlers without privileged services."""
import base64
import io
import json
from pathlib import Path
import socketserver
from types import SimpleNamespace
import uuid

import pytest

from test_regressions import panel, config, deployment, PASSWORD
from test_dashboard import browser, login
from control import Controller, TITLES

CONTRACT = json.loads((Path(__file__).resolve().parents[1] / "specs/003-dashboard-presets/contracts/http.json").read_text(encoding="utf-8"))


def test_http_route_inventory_and_unauthenticated_status(browser):
    actual = {(method, route.path) for route in panel.app.routes if hasattr(route, "methods") for method in route.methods}
    expected = {(row["method"], row["path"]) for row in CONTRACT["routes"]}
    assert actual == expected
    for row in CONTRACT["routes"]:
        if row.get("anonymous_status") is not None:
            path = row["path"].replace("{filename}", "freenetvpn-20260911-120000.tar.gz")
            response = browser.request(row["method"], path, json={})
            assert response.status_code == row["anonymous_status"], (path, response.text)


def test_login_limits_export_and_job_wire_contract(browser, deployment, monkeypatch):
    limits = CONTRACT["login"]
    for field in ["username", "password"]:
        body = {"username": "admin", "password": PASSWORD}
        body[field] = "a" * (limits[field + "_max"] + 1)
        assert browser.post("/admin/api/login", json=body, headers={"Origin": "https://vpn.example.test"}).status_code == 422
    headers = login(browser)
    controller = Controller(deployment, worker=False)
    def dispatch(method, data=None):
        if method == "submit":
            return controller.submit(data)
        return controller.export(**data)
    monkeypatch.setattr(panel, "control", dispatch)
    body = {"operation": "backup.create", "request_id": str(uuid.uuid4())}
    response = browser.post("/admin/api/jobs", json=body, headers=headers)
    assert response.status_code == 202
    assert set(response.json()) == set(CONTRACT["queued_job_fields"])
    assert response.json()["status"] == "queued"
    assert browser.post("/admin/api/jobs", json=body, headers=headers).json() == response.json()
    exported = browser.get("/admin/api/export?protocol=vless&name=legacy").json()
    assert set(exported) == set(CONTRACT["export_fields"])
    assert base64.b64decode(exported["content"], validate=True).startswith(b"vless://")
    assert set(TITLES) == set(CONTRACT["operations"])


@pytest.mark.skipif(not hasattr(socketserver, "ThreadingUnixStreamServer"), reason="Unix agent is Linux-only")
@pytest.mark.parametrize("case", ["snapshot", "invalid_token", "unknown_method", "unknown_job_field", "oversized", "missing_newline"])
def test_actual_agent_framing_and_authorization(deployment, case):
    from control_agent import Handler
    request = {"token": "a"*64, "method": "snapshot"}
    if case == "invalid_token":
        request["token"] = "wrong"
    elif case == "unknown_method":
        request["method"] = "exec"
    elif case == "unknown_job_field":
        request.update(method="submit", data={"operation": "backup.create", "command": "id"})
    raw = json.dumps(request).encode() + b"\n"
    if case == "oversized":
        raw = b" " * CONTRACT["agent_request_max_bytes"] + b"\n"
    elif case == "missing_newline":
        raw = raw.rstrip(b"\n")
    controller = Controller(deployment, worker=False)
    calls = []
    controller.snapshot = lambda: calls.append("snapshot") or {"services": []}
    handler = Handler.__new__(Handler)
    handler.connection = SimpleNamespace(settimeout=lambda value: None)
    handler.server = SimpleNamespace(token="a"*64, controller=controller)
    handler.rfile, handler.wfile = io.BytesIO(raw), io.BytesIO()
    handler.handle()
    response = json.loads(handler.wfile.getvalue())
    assert response["ok"] is (case == "snapshot")
    assert calls == (["snapshot"] if case == "snapshot" else [])
    assert not controller.jobs
    assert set(response) == ({"ok", "data"} if case == "snapshot" else {"ok", "error"})
