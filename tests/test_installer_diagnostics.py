"""Operator recovery and failure-boundary tests; no DNS or host changes."""
import argparse
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import diagnostics as diag
import manage


@pytest.fixture(autouse=True)
def english(monkeypatch):
    monkeypatch.setenv("FREENET_LANG", "en")


def arguments(**overrides):
    return argparse.Namespace(**(dict(domain=None, wg_domain=None, email=None,
        password_stdin=False, admin_user="admin", wg_port=51820, services="wireguard,vless") | overrides))


def config():
    return dict(DOMAIN="vpn.example.test", WG_DOMAIN="wg.example.test", COMPOSE_PROFILES="wireguard,vless")


@pytest.mark.parametrize("domain,wg,code", [
    ("https://vpn.example.test", "wg.example.test", "CONFIG_DOMAIN"),
    ("vpn.example.test", "VPN.EXAMPLE.TEST", "CONFIG_HOSTS_EQUAL"),
])
def test_invalid_cli_domains_do_not_read_password_or_write_state(tmp_path, monkeypatch, domain, wg, code):
    def forbidden(*a, **kw):
        pytest.fail("input/password requested for invalid CLI domains")
    monkeypatch.setattr("builtins.input", forbidden)
    monkeypatch.setattr(manage.getpass, "getpass", forbidden)
    with pytest.raises(diag.ConfigurationIssue, match=code):
        manage.configure(arguments(domain=domain, wg_domain=wg), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_interactive_correction_precedes_password_and_saves_once(tmp_path, monkeypatch, capsys):
    replies = iter(["https://bad.test", "VPN.EXAMPLE.TEST", "vpn.example.test", "wg.example.test", "admin@example.test"])
    prompts = []
    def answer(prompt):
        prompts.append(prompt)
        assert not (tmp_path / ".env").exists()
        return next(replies)
    def password(prompt):
        assert len(prompts) == 5
        return "installer test password"
    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(manage.getpass, "getpass", password)
    manage.configure(arguments(), tmp_path)
    saved = manage.read_config(tmp_path)
    assert saved["DOMAIN"] == "vpn.example.test"
    assert saved["WG_DOMAIN"] == "wg.example.test"
    error = capsys.readouterr().err
    assert "CONFIG_DOMAIN" in error and "CONFIG_HOSTS_EQUAL" in error
    assert "DNS has not been checked" in error
    before = (tmp_path / ".env").read_bytes()
    monkeypatch.setattr("builtins.input", lambda *a: pytest.fail("prompted on resume"))
    manage.configure(arguments(), tmp_path)
    assert (tmp_path / ".env").read_bytes() == before


@pytest.mark.parametrize("saved", [False, True])
@pytest.mark.parametrize("language", ["en", "ru"])
def test_resume_reflects_state_language_and_firewall(tmp_path, monkeypatch, capsys, saved, language):
    monkeypatch.setenv("FREENET_LANG", language)
    if saved:
        (tmp_path / ".env").write_text("SECRET_SENTINEL", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    diag.resume(tmp_path, no_firewall=True)
    text = capsys.readouterr().err
    assert ("--existing" in text) == saved
    assert "--no-firewall" in text
    assert "SECRET_SENTINEL" not in text
    assert ("После исправления" if language == "ru" else "After fixing") in text
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize("failure,code", [(False, "DNS_NO_IPV4"), (True, "DNS_LOOKUP_FAILED")])
def test_dns_no_answer_or_timeout_is_actionable(tmp_path, monkeypatch, capsys, failure, code):
    def lookup(host, family):
        if failure:
            raise subprocess.TimeoutExpired("getent", 6)
        return []
    monkeypatch.setattr(diag, "lookup", lookup)
    assert diag.dns(config(), tmp_path) == 1
    text = capsys.readouterr().err
    assert code in text and "getent ahostsv4 vpn.example.test" in text
    assert "sudo bash install.sh" in text
    assert list(tmp_path.iterdir()) == []


def test_dns_reports_observations_without_claiming_ip_match(tmp_path, monkeypatch, capsys):
    calls = []
    def lookup(host, family):
        calls.append((host, family))
        return ["192.0.2.9"] if family == 4 else ["2001:db8::9"]
    monkeypatch.setattr(diag, "lookup", lookup)
    assert diag.dns(config() | {"COMPOSE_PROFILES": "vless"}, tmp_path) == 0
    output = capsys.readouterr().out
    assert "192.0.2.9" in output and "AAAA" in output
    assert "does not prove global DNS propagation" in output
    assert calls == [("vpn.example.test", 4), ("vpn.example.test", 6)]


def test_getent_is_bounded_and_addresses_are_deduplicated(monkeypatch):
    def run(argv, **kw):
        assert argv == ["getent", "ahostsv4", "vpn.example.test"]
        assert kw["timeout"] == 6 and not kw["check"]
        return subprocess.CompletedProcess(argv, 0, "192.0.2.9 STREAM\n192.0.2.9 DGRAM\n")
    monkeypatch.setattr(diag.subprocess, "run", run)
    assert diag.lookup("vpn.example.test", 4) == ["192.0.2.9"]


@pytest.mark.parametrize("curl,status,auth,expected", [
    (6, 0, False, "HTTPS_DNS"), (7, 0, False, "HTTPS_CONNECT"),
    (28, 0, False, "HTTPS_TIMEOUT"), (60, 0, False, "HTTPS_TLS"),
    (0, 502, True, "HTTPS_BACKEND"), (0, 503, False, "HTTPS_BACKEND"),
    (0, 200, True, "HTTPS_AUTH"), (0, 200, False, "HTTPS_RESPONSE"),
])
def test_https_categories_include_evidence_fix_and_safe_resume(tmp_path, capsys, curl, status, auth, expected):
    (tmp_path / ".env").write_text("SECRET_SENTINEL", encoding="utf-8")
    assert diag.https_failure(tmp_path, config(), curl, status, "wireguard", auth, True) == 1
    text = capsys.readouterr().err
    assert expected in text and f"curl={curl}, HTTP={status}" in text
    assert "wg.example.test" in text and "Fix:" in text and "Check:" in text
    assert "sudo bash install.sh --existing --no-firewall" in text
    assert "SECRET_SENTINEL" not in text and "--insecure" not in text
    assert (tmp_path / ".env").read_text() == "SECRET_SENTINEL"


def test_subprocess_error_does_not_print_argv(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["manage.py", "compose", "ps"])
    def failed(*a):
        raise subprocess.CalledProcessError(42, ["example", "SECRET_SENTINEL"])
    monkeypatch.setattr(manage, "compose", failed)
    assert manage.main() == 1
    error = capsys.readouterr().err
    assert "42" in error and "SECRET_SENTINEL" not in error
