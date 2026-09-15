import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import manage
import protocols


@pytest.fixture
def extra(tmp_path):
    config = dict(**manage.PORT_DEFAULTS, CONFIG_VERSION="2", DOMAIN="vpn.example.test", WG_DOMAIN="wg.example.test",
                  LE_EMAIL="ci@example.test", ADMIN_USER="admin", ADMIN_PASSWORD_HASH=manage.password_hash("testing-long-password"),
                  WG_PORT="51820", DNS1="1.1.1.1", DNS2="8.8.8.8", COMPOSE_PROFILES="ikev2,l2tp,outline,amnezia",
                  VLESS_UUID="9ab3b0aa-4a2b-44b7-acd4-5a644eec3c89", VLESS_WS_PATH="/assets-protocols")
    manage.write_config(config, tmp_path)
    manage.render(config, tmp_path)
    key = {"private": "A"*43 + "=", "public": "B"*43 + "="}
    state = {"version": 1, "clients": {"ikev2": {}, "l2tp": {}, "amnezia": {}}, "ipsec_psk": "test-psk-value",
             "awg": {**key, "params": {"Jc": 4, "Jmin": 40, "Jmax": 70, "S1": 16, "S2": 24, "S3": 16, "S4": 16,
                                            "H1": 10123456, "H2": 20123456, "H3": 30123456, "H4": 40123456}}, "outline_prefix": "test-api-prefix"}
    protocols.save(state, tmp_path)
    return tmp_path, config


@pytest.mark.parametrize("name", ["../escape", "x\n: PSK bad", "", "a b", "x;id"])
def test_reject_unsafe_client_names(extra, name):
    root, _ = extra
    original = protocols.state_file(root).read_bytes()
    with pytest.raises(ValueError):
        protocols.client("add", "l2tp", name, root)
    assert protocols.state_file(root).read_bytes() == original


@pytest.mark.parametrize("key,value", [("AWG_PORT", "51820"), ("OUTLINE_PORT", "65536"), ("OUTLINE_API_PORT", "22"), ("AWG_PORT", "5;id")])
def test_invalid_extra_ports(extra, key, value):
    _, config = extra
    with pytest.raises(ValueError):
        manage.validate(dict(config, **{key: value}))


def test_l2tp_lifecycle_and_duplicate_preserve_credentials(extra, monkeypatch):
    root, _ = extra
    calls = []
    monkeypatch.setattr(manage, "compose", lambda args, root: calls.append(args))
    protocols.client("add", "l2tp", "phone", root)
    original = protocols.read_state(root)["clients"]["l2tp"]["phone"]
    assert calls[-1][-1] == "ipsec"
    with pytest.raises(ValueError):
        protocols.client("add", "l2tp", "phone", root)
    assert original == protocols.read_state(root)["clients"]["l2tp"]["phone"]
    export = root / "data/exports/l2tp/phone.json"
    assert json.loads(export.read_text())["password"] == original["password"]
    protocols.client("revoke", "l2tp", "phone", root)
    assert not export.exists()
    assert "phone" not in (root / "runtime/ipsec/chap-secrets").read_text()


def test_amnezia_export_matches_server_obfuscation_and_revoke(extra, monkeypatch):
    root, _ = extra
    monkeypatch.setattr(protocols, "keypair", lambda: {"private": "C"*43+"=", "public": "D"*43+"="})
    monkeypatch.setattr(manage, "compose", lambda args, root: None)
    protocols.client("add", "amnezia", "phone", root)
    exported = (root / "data/exports/amnezia/phone.conf").read_text()
    assert "Address = 10.98.0.2/32" in exported
    assert "Endpoint = vpn.example.test:51830" in exported
    assert "S4 = 16" in exported and "H4 = 40123456" in exported
    protocols.client("revoke", "amnezia", "phone", root)
    assert "[Peer]" not in (root / "runtime/amnezia/awg0.conf").read_text()


def test_single_protocol_render_disables_other_ipsec_mode(extra):
    root, config = extra
    protocols.render(dict(config, COMPOSE_PROFILES="ikev2"), root)
    assert "conn l2tp" not in (root / "runtime/ipsec/ipsec.conf").read_text()
    assert "PSK" not in (root / "runtime/ipsec/ipsec.secrets").read_text()
    assert "ENABLE_L2TP=false" in (root / "runtime/ipsec.env").read_text()


def test_protocol_secrets_survive_backup_restore(extra, monkeypatch, tmp_path):
    root, _ = extra
    original = protocols.state_file(root).read_bytes()
    monkeypatch.setattr(manage, "compose", lambda args, root, **kw: subprocess.CompletedProcess(args, 0, "", ""))
    archive = manage.make_backup(root)
    restored = tmp_path / "restored"
    restored.mkdir()
    manage.restore(archive, restored)
    assert protocols.state_file(restored).read_bytes() == original


def test_old_v2_configuration_gets_port_defaults_without_file_changes(extra):
    root, config = extra
    for key in manage.PORT_DEFAULTS:
        config.pop(key)
    manage.write_config(config, root)
    before = (root / ".env").read_bytes()
    assert manage.read_config(root)["AWG_PORT"] == "51830"
    assert (root / ".env").read_bytes() == before


def test_no_plaintext_l2tp_or_public_outline_api():
    compose = yaml.safe_load((Path(__file__).resolve().parents[1] / "docker-compose.yml").read_text())
    ipsec = compose["services"]["ipsec"]
    assert ipsec["profiles"] == ["ikev2", "l2tp"]
    assert all("1701" not in p for p in ipsec["ports"])
    assert "privileged" not in ipsec
    assert compose["services"]["outline"]["ports"][0].startswith("127.0.0.1:")


def test_outline_failed_rename_removes_partial_key(extra, monkeypatch):
    root, _ = extra
    calls = []
    def fake_api(config, root, path, method="GET", body=None):
        calls.append((path, method))
        if method == "GET":
            return {"accessKeys": []}
        if method == "POST":
            return {"id": "3"}
        if method == "PUT":
            raise OSError("Name update failed")
        return {}
    monkeypatch.setattr(protocols, "outline_api", fake_api)
    with pytest.raises(OSError):
        protocols.client("add", "outline", "phone", root)
    assert calls[-1] == ("access-keys/3", "DELETE")


def test_prepare_refuses_breaking_existing_outline_port(extra, monkeypatch):
    root, config = extra
    state = protocols.read_state(root)
    state["outline_port"] = "2443"
    protocols.save(state, root)
    original = protocols.state_file(root).read_bytes()
    monkeypatch.setattr(protocols, "certificate", lambda root, domain: None)
    with pytest.raises(ValueError, match="port change"):
        protocols.prepare(dict(config, OUTLINE_PORT="2444"), root)
    assert protocols.state_file(root).read_bytes() == original


@pytest.mark.skipif(shutil.which("openssl") is None, reason="OpenSSL required; exercised by both Linux CI runners")
def test_real_pki_and_keys_are_preserved_on_prepare(extra):
    root, config = extra
    protocols.state_file(root).unlink()
    protocols.prepare(config, root)
    originals = {p: p.read_bytes() for p in (root / "data").rglob("*") if p.is_file()}
    protocols.prepare(config, root)
    assert all(p.read_bytes() == value for p,value in originals.items())
    state = protocols.read_state(root)
    state["clients"]["ikev2"]["phone"] = {"password": "test-password"}
    protocols.export_client("ikev2", "phone", config, state, root)
    assert (root / "data/exports/ikev2/phone.mobileconfig").exists()
