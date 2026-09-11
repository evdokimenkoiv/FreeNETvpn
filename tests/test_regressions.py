import argparse
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import manage

spec = importlib.util.spec_from_file_location("freenet_admin", ROOT / "admin/app/main.py")
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)
PASSWORD = "correct horse battery staple"


@pytest.fixture
def config():
    return dict(CONFIG_VERSION="2", DOMAIN="vpn.example.test", WG_DOMAIN="wg.example.test",
                LE_EMAIL="admin@example.test", ADMIN_USER="admin", ADMIN_PASSWORD_HASH=manage.password_hash(PASSWORD),
                WG_PORT="52999", DNS1="1.1.1.1", DNS2="8.8.8.8", COMPOSE_PROFILES="wireguard,vless",
                VLESS_UUID="9ab3b0aa-4a2b-44b7-acd4-5a644eec3c89", VLESS_WS_PATH="/assets-testpath123")


@pytest.fixture
def deployment(tmp_path, config):
    manage.write_config(config, tmp_path)
    manage.render(config, tmp_path)
    return tmp_path


@pytest.fixture
def client(deployment, monkeypatch):
    monkeypatch.setattr(panel, "CONFIG", deployment / "runtime/admin.json")
    monkeypatch.setattr(panel, "BACKUPS", deployment / "backups")
    with TestClient(panel.app) as client:
        yield client


@pytest.mark.parametrize("path", ["/admin", "/admin/", "/admin/status", "/admin/backups", "/admin/backup", "/auth"])
def test_administrative_routes_require_auth(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, auth=("admin", "incorrect password")).status_code == 401


def test_admin_correct_password_does_not_crash(client):
    response = client.get("/admin", auth=("admin", PASSWORD))
    assert response.status_code == 200
    assert "wg.example.test" in response.text
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/auth", auth=("admin", PASSWORD)).status_code == 200


def test_no_host_command_or_docker_access(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Host command executed by panel")
    monkeypatch.setattr(subprocess, "run", forbidden)
    def unavailable(*args, **kwargs):
        raise OSError("Offline test")
    monkeypatch.setattr(panel.socket, "create_connection", unavailable)
    response = client.get("/admin/status", auth=("admin", PASSWORD))
    assert response.status_code == 200
    assert set(response.json()["checks"].values()) == {"unreachable"}


def test_backup_requires_auth_and_handles_absence(client, deployment):
    assert client.get("/admin/backup", auth=("admin", PASSWORD)).status_code == 404
    path = deployment / "backups/freenetvpn-test.tar.gz"
    path.write_bytes(b"private backup")
    assert client.get("/admin/backups/freenetvpn-test.tar.gz").status_code == 401
    response = client.get("/admin/backup", auth=("admin", PASSWORD))
    assert response.content == b"private backup"
    assert response.headers["cache-control"] == "no-store"


def test_reconfigure_preserves_all_keys_and_clients(deployment, config):
    client_data = deployment / "data/wireguard/wg0.json"
    client_data.parent.mkdir(parents=True)
    client_data.write_text('{"privateKey":"keep-me"}')
    original = (deployment / ".env").read_bytes()
    manage.configure(argparse.Namespace(domain=None, wg_domain=None, email=None), deployment)
    assert (deployment / ".env").read_bytes() == original
    assert "keep-me" in client_data.read_text()
    assert manage.read_config(deployment) == config


def test_legacy_config_is_not_overwritten(tmp_path):
    original = "DOMAIN=old.example.com\nADMIN_PASS=do-not-overwrite\n"
    (tmp_path / ".env").write_text(original)
    with pytest.raises(ValueError):
        manage.configure(argparse.Namespace(), tmp_path)
    assert (tmp_path / ".env").read_text() == original


@pytest.mark.parametrize("key,value", [
    ("DOMAIN", "example.com\nreverse_proxy bad:8000"),
    ("WG_DOMAIN", "https://wg.example.com/path"),
    ("WG_PORT", "65536"), ("WG_PORT", "22"),
    ("COMPOSE_PROFILES", "all"), ("COMPOSE_PROFILES", "vless,outline"),
    ("VLESS_UUID", "${VLESS_UUID}"), ("VLESS_WS_PATH", "/admin"),
    ("LE_EMAIL", "$(id)@example.com"), ("DNS1", "1.1.1.1;id"),
])
def test_invalid_configuration_is_rejected(config, key, value):
    config[key] = value
    with pytest.raises(ValueError):
        manage.validate(config)


def test_environment_comments_not_part_of_uuid():
    assert manage.parse_env('VLESS_UUID=   # generate me\n')["VLESS_UUID"] == ""
    with pytest.raises(ValueError):
        manage.parse_env("DOMAIN=one.example\nDOMAIN=other.example")


def test_rendered_protocol_contract(deployment, config):
    xray = json.loads((deployment / "runtime/xray.json").read_text())
    inbound = xray["inbounds"][0]
    assert inbound["settings"]["clients"][0]["id"] == config["VLESS_UUID"]
    assert inbound["streamSettings"]["wsSettings"]["path"] == config["VLESS_WS_PATH"]
    uri = urlsplit(manage.client_uri(config))
    assert parse_qs(uri.query)["path"] == [config["VLESS_WS_PATH"]]
    caddy = (deployment / "runtime/Caddyfile").read_text()
    assert "handle_path" not in caddy
    assert "@admin path /admin /admin/*" in caddy
    assert "forward_auth admin:8000" in caddy
    assert "${" not in json.dumps(xray)
    assert PASSWORD not in (deployment / "runtime/admin.json").read_text()


@pytest.mark.parametrize("services,enabled,disabled", [("vless", "xray:10000", "wg-easy:51821"), ("wireguard", "wg-easy:51821", "xray:10000")])
def test_profiles_control_rendered_routes(tmp_path, config, services, enabled, disabled):
    config["COMPOSE_PROFILES"] = services
    manage.render(config, tmp_path)
    caddy = (tmp_path / "runtime/Caddyfile").read_text()
    assert enabled in caddy
    assert disabled not in caddy


def test_compose_ports_and_privileges():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = compose["services"]
    assert any(p.endswith("/udp") for p in services["wg-easy"]["ports"])
    assert "ports" not in services["admin"] and "ports" not in services["xray"]
    assert "docker.sock" not in json.dumps(compose)
    assert "fetch(" in json.dumps(services["wg-easy"]["healthcheck"])


def test_backup_restore_roundtrip_preserves_credentials_and_state(deployment, config, tmp_path, monkeypatch):
    data = deployment / "data/wireguard"
    data.mkdir(parents=True)
    (data / "wg0.db").write_bytes(b"sample client database")
    calls = []
    def fake_compose(args, root, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "admin\nwg-easy\nxray\n", "")
    monkeypatch.setattr(manage, "compose", fake_compose)
    archive = manage.make_backup(deployment)
    assert calls[1] == ["stop", "admin", "wg-easy", "xray"]
    assert calls[-1] == ["start", "admin", "wg-easy", "xray"]
    restored = tmp_path / "restored"
    restored.mkdir()
    manage.restore(archive, restored)
    assert manage.read_config(restored) == config
    assert (restored / "data/wireguard/wg0.db").read_bytes() == b"sample client database"
    with pytest.raises(ValueError, match="empty installation"):
        manage.restore(archive, restored)


@pytest.mark.parametrize("name,link", [("../escape", False), ("/etc/passwd", False), ("data/link", True), ("data/../../escape", False), ("runtime\\evil", False)])
def test_archive_traversal_and_links_rejected(tmp_path, name, link):
    path = tmp_path / "bad.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo(name)
        if link:
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc"
            archive.addfile(member)
        else:
            member.size = 3
            archive.addfile(member, io.BytesIO(b"bad"))
    with tarfile.open(path, "r:gz") as archive:
        with pytest.raises(ValueError, match="Unsafe"):
            manage.checked_members(archive)


def test_rotation_restores_original_configuration_on_validation_failure(deployment, config, monkeypatch):
    monkeypatch.setattr(manage, "make_backup", lambda root: None)
    calls = []
    def failing_compose(args, root):
        calls.append(args)
        if args[0] == "run":
            raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(manage, "compose", failing_compose)
    with pytest.raises(subprocess.CalledProcessError):
        manage.rotate_vless(deployment)
    assert manage.read_config(deployment) == config
    assert json.loads((deployment / "runtime/xray.json").read_text())["inbounds"][0]["settings"]["clients"][0]["id"] == config["VLESS_UUID"]
    assert calls[-1][-2:] == ["caddy", "xray"]


def test_services_resume_even_if_backup_fails(deployment, monkeypatch):
    calls = []
    def fake_compose(args, root, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "admin\nxray\n", "")
    monkeypatch.setattr(manage, "compose", fake_compose)
    def fail_archive(*args, **kwargs):
        raise OSError("Disk full")
    monkeypatch.setattr(tarfile, "open", fail_archive)
    with pytest.raises(OSError, match="Disk full"):
        manage.make_backup(deployment)
    assert calls[-1] == ["start", "admin", "xray"]
