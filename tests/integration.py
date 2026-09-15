"""Real TLS and VPN packet tests. Run ONLY in an empty disposable Linux checkout."""
import json
import base64
import uuid
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import manage

PASSWORD = "CI-only-password-123456789"
BASE = ["docker", "compose", "-p", "freenetvpn", "--env-file", ".env", "-f", "docker-compose.yml", "-f", "runtime/compose.ci.yml"]
ENV = dict(os.environ, COMPOSE_PROFILES="wireguard,vless")


def run(args, check=True):
    return subprocess.run(args, cwd=ROOT, env=ENV, text=True, capture_output=True, check=check)


def dc(*args, check=True):
    return run(BASE + list(args), check=check)


def web(path, host="vpn.example.test", auth=False, body=None, expected=200, headers=None):
    args = ["curl", "-sS", "--noproxy", "*", "--max-time", "15", "--cacert", "runtime/ci-ca.crt",
            "--resolve", f"{host}:18443:127.0.0.1", "-w", "\n%{http_code}",
            "-b", "runtime/ci.cookies", "-c", "runtime/ci.cookies"]
    if auth:
        args += ["--user", f"admin:{PASSWORD}"]
    if body is not None:
        origin = f"https://{host}" if path.startswith("/admin/") else f"https://{host}:18443"
        args += ["-H", "Content-Type: application/json", "-H", f"Origin: {origin}", "-d", json.dumps(body)]
    for key, value in (headers or {}).items():
        args += ["-H", f"{key}: {value}"]
    result = run(args + [f"https://{host}:18443{path}"])
    content, status = result.stdout.rsplit("\n", 1)
    assert int(status) == expected, (path, status, content[:500])
    return content


def main():
    if (ROOT / ".env").exists() or (ROOT / "data").exists():
        raise RuntimeError("Tests require an EMPTY disposable checkout")
    config = dict(CONFIG_VERSION="2", DOMAIN="vpn.example.test", WG_DOMAIN="wg.example.test",
                  LE_EMAIL="ci@example.test", ADMIN_USER="admin", ADMIN_PASSWORD_HASH=manage.password_hash(PASSWORD),
                  WG_PORT="52999", DNS1="1.1.1.1", DNS2="8.8.8.8", COMPOSE_PROFILES="wireguard,vless",
                  VLESS_UUID="9ab3b0aa-4a2b-44b7-acd4-5a644eec3c89", VLESS_WS_PATH="/assets-ci-validation")
    manage.write_config(config)
    manage.render(config)
    runtime = ROOT / "runtime"
    # Real unprivileged web container -> authenticated Unix socket -> host agent.
    # CI invokes the same systemd unit installer used on production hosts.
    run(["sudo", "bash", "scripts/install_control.sh"])
    caddy = (runtime / "Caddyfile").read_text()
    for host in (config["DOMAIN"], config["WG_DOMAIN"]):
        caddy = caddy.replace(host + " {", host + " {\n  tls internal")
    (runtime / "Caddyfile").write_text(caddy)
    (runtime / "echo").mkdir()
    (runtime / "echo/probe.txt").write_text("freenetvpn-tunnel-ok")
    (runtime / "wg-client").mkdir()
    (runtime / "client-build").mkdir()
    (runtime / "client-build/Dockerfile").write_text('FROM alpine:3.22\nRUN apk add --no-cache wireguard-tools iproute2 curl iptables\nCMD ["sleep", "infinity"]\n')
    (runtime / "compose.ci.yml").write_text('''services:
  caddy:
    ports: !override ["127.0.0.1:18443:443"]
  echo-server:
    image: python:3.12-slim
    working_dir: /srv
    command: [python, -m, http.server, "18080", --bind, 0.0.0.0]
    volumes: ["./runtime/echo:/srv:ro"]
    networks: [backend]
  xray-client:
    image: ghcr.io/xtls/xray-core:26.3.27
    profiles: [test-client]
    command: [run, -config, /etc/xray/client.json]
    ports: ["127.0.0.1:11080:1080"]
    volumes:
      - ./runtime/xray-client.json:/etc/xray/client.json:ro
      - ./runtime/ci-ca.crt:/etc/xray/ca.crt:ro
    networks: [backend]
  wg-client:
    build: ./runtime/client-build
    profiles: [test-client]
    cap_add: [NET_ADMIN]
    sysctls:
      net.ipv4.conf.all.src_valid_mark: "1"
    volumes: ["./runtime/wg-client:/etc/wireguard"]
    networks: [backend]
''')
    try:
        dc("config", "--quiet")
        print(dc("up", "-d", "--build", "--wait", "--wait-timeout", "180").stdout, flush=True)
        dc("exec", "-T", "xray", "/usr/local/bin/xray", "run", "-test", "-config", "/etc/xray/config.json")
        for _ in range(30):
            if dc("cp", "caddy:/data/caddy/pki/authorities/local/root.crt", "runtime/ci-ca.crt", check=False).returncode == 0:
                break
            time.sleep(2)
        os.chmod(runtime / "ci-ca.crt", 0o644)
        assert json.loads(web("/healthz"))["status"] == "ok"
        web("/admin", expected=401)
        web("/", host=config["WG_DOMAIN"], expected=401)
        assert "FreeNETvpn" in web("/admin", auth=True)
        print("PASS: real HTTPS certificate validation, admin authentication, WireGuard UI protection", flush=True)
        client_config = {"log": {"loglevel": "warning"},
            "inbounds": [{"listen": "0.0.0.0", "port": 1080, "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [{"protocol": "vless", "settings": {"vnext": [{"address": "caddy", "port": 443,
                "users": [{"id": config["VLESS_UUID"], "encryption": "none"}]}]},
                "streamSettings": {"network": "ws", "security": "tls", "tlsSettings": {"serverName": config["DOMAIN"],
                    "certificates": [{"usage": "verify", "certificateFile": "/etc/xray/ca.crt"}]},
                    "wsSettings": {"path": config["VLESS_WS_PATH"], "headers": {"Host": config["DOMAIN"]}}}}]}
        (runtime / "xray-client.json").write_text(json.dumps(client_config))
        dc("up", "-d", "xray-client")
        time.sleep(3)
        tunnel = run(["curl", "-fsS", "--max-time", "20", "--socks5-hostname", "127.0.0.1:11080", "http://echo-server:18080/probe.txt"])
        assert tunnel.stdout == "freenetvpn-tunnel-ok"
        print("PASS: VLESS -> WebSocket -> validated TLS -> Caddy -> Xray -> HTTP payload", flush=True)
        # Exercise the same protected first-run wizard used by a real installation.
        assert json.loads(web("/api/setup/2", host=config["WG_DOMAIN"], auth=True,
                              body={"username": "admin", "password": PASSWORD, "confirmPassword": PASSWORD}))["success"]
        wg_id = dc("ps", "-q", "wg-easy").stdout.strip()
        wg_ip = run(["docker", "inspect", "-f", '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', wg_id]).stdout.strip()
        assert json.loads(web("/api/setup/4", host=config["WG_DOMAIN"], auth=True,
                              body={"host": wg_ip, "port": 52999}))["success"]
        login = json.loads(web("/api/auth/password", host=config["WG_DOMAIN"], auth=True,
                               body={"username": "admin", "password": PASSWORD, "remember": False}))
        assert login["status"] == "success", login
        peer = json.loads(web("/api/client", host=config["WG_DOMAIN"], auth=True, body={"name": "CI-test-client", "expiresAt": None}))
        wireguard = web(f"/api/client/{peer['clientId']}/configuration", host=config["WG_DOMAIN"], auth=True)
        # Keep Docker's own routing/DNS; explicitly route the probe through wg0.
        # wg-quick's full-default-route setup writes read-only /proc/sys in Docker.
        wireguard = "\n".join(line for line in wireguard.splitlines() if not line.startswith("DNS =")) + "\n"
        wireguard = wireguard.replace("[Interface]", "[Interface]\nTable = off")
        (runtime / "wg-client/wg0.conf").write_text(wireguard)
        dc("up", "-d", "--build", "wg-client")
        dc("exec", "-T", "wg-client", "wg-quick", "up", "wg0")
        echo_id = dc("ps", "-q", "echo-server").stdout.strip()
        echo_ip = run(["docker", "inspect", "-f", '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', echo_id]).stdout.strip()
        dc("exec", "-T", "wg-client", "ip", "route", "add", echo_ip + "/32", "dev", "wg0")
        packet = dc("exec", "-T", "wg-client", "curl", "-fsS", "--max-time", "20", "--interface", "wg0", f"http://{echo_ip}:18080/probe.txt")
        assert packet.stdout == "freenetvpn-tunnel-ok"
        handshakes = dc("exec", "-T", "wg-client", "wg", "show", "wg0", "latest-handshakes").stdout.splitlines()
        assert any(int(line.split()[1]) > 0 for line in handshakes)
        print("PASS: WireGuard login, create/export client, real handshake and HTTP routed through wg0", flush=True)
        session = json.loads(web("/admin/api/login", body={"username": "admin", "password": PASSWORD}))
        csrf = {"X-CSRF-Token": session["csrf"]}

        def job(operation, **fields):
            submitted = json.loads(web("/admin/api/jobs", body=dict(operation=operation, request_id=str(uuid.uuid4()), **fields), headers=csrf, expected=202))
            for _ in range(90):
                overview = json.loads(web("/admin/api/overview"))
                current = next(j for j in overview["jobs"] if j["id"] == submitted["id"])
                if current["status"] == "done":
                    return current
                assert current["status"] not in {"failed", "interrupted"}, current
                time.sleep(2)
            raise AssertionError("Dashboard operation timed out")

        web("/admin/api/jobs", body={"operation": "service.restart", "protocol": "vless"}, expected=403)
        job("wireguard.connect", protocol="wireguard", username="admin", password=PASSWORD)
        job("client.add", protocol="wireguard", name="dashboard-peer")
        exported = json.loads(web("/admin/api/export?protocol=wireguard&name=dashboard-peer"))
        assert "PrivateKey" in base64.b64decode(exported["content"]).decode()
        job("client.revoke", protocol="wireguard", name="dashboard-peer")
        assert not any(c["name"] == "dashboard-peer" for c in json.loads(web("/admin/api/overview"))["clients"])
        print("PASS: dashboard session/CSRF, systemd Unix agent, native WireGuard create/export/revoke", flush=True)
        for preset in ("ws-tls", "mobile-ws", "grpc-tls"):
            job("client.add", protocol="vless", name="ci-" + preset, preset=preset)
            exported = json.loads(web("/admin/api/export?protocol=vless&name=ci-" + preset + "&format=json"))
            profile = json.loads(base64.b64decode(exported["content"]))
            profile["inbounds"][0]["listen"] = "0.0.0.0"
            outbound = profile["outbounds"][0]
            outbound["settings"]["vnext"][0]["address"] = "caddy"
            outbound["streamSettings"]["tlsSettings"]["certificates"] = [{"usage": "verify", "certificateFile": "/etc/xray/ca.crt"}]
            (runtime / "xray-client.json").write_text(json.dumps(profile))
            dc("up", "-d", "--force-recreate", "xray-client")
            time.sleep(3)
            packet = run(["curl", "-fsS", "--max-time", "20", "--socks5-hostname", "127.0.0.1:11080", "http://echo-server:18080/probe.txt"])
            assert packet.stdout == "freenetvpn-tunnel-ok"
            assert "<svg" in web("/admin/api/qr?protocol=vless&name=ci-" + preset)
            job("client.revoke", protocol="vless", name="ci-" + preset)
            dc("restart", "xray-client")
            rejected = run(["curl", "-fsS", "--max-time", "5", "--socks5-hostname", "127.0.0.1:11080", "http://echo-server:18080/probe.txt"], check=False)
            assert rejected.returncode != 0
            print("PASS: dashboard VLESS " + preset + " create, JSON/QR export, TLS payload and revoked-client rejection", flush=True)
        job("service.stop", protocol="vless")
        assert next(s for s in json.loads(web("/admin/api/overview"))["services"] if s["id"] == "vless")["state"] != "running"
        job("service.start", protocol="vless")
        assert next(s for s in json.loads(web("/admin/api/overview"))["services"] if s["id"] == "vless")["state"] == "running"
        # Remove only disposable probe containers: production backups handle the
        # configured services, never these CI-only Compose overrides.
        dc("rm", "-s", "-f", "xray-client", "wg-client", "echo-server")
        # Client mutations render the production Caddy config. A container start
        # remounts that file; restore only this test's private-CA override before
        # exercising backup/recovery (public ACME cannot issue for .test).
        manage.atomic_write(runtime / "Caddyfile", caddy, 0o644)
        submitted = json.loads(web("/admin/api/jobs", body={"operation": "backup.create", "request_id": str(uuid.uuid4())}, headers=csrf, expected=202))
        for _ in range(90):
            try:
                current = next(j for j in json.loads(web("/admin/api/overview", auth=True))["jobs"] if j["id"] == submitted["id"])
                if current["status"] == "done":
                    break
                assert current["status"] not in {"failed", "interrupted"}, current
            except (subprocess.CalledProcessError, AssertionError) as error:
                if isinstance(error, AssertionError) and 'current' in locals() and current.get("status") in {"failed", "interrupted"}:
                    raise
            time.sleep(2)
        else:
            raise AssertionError("Backup did not resume the dashboard")
        filename = current["result"]["filename"]
        response = run(["curl", "-fsS", "--noproxy", "*", "--max-time", "30", "--cacert", "runtime/ci-ca.crt", "--resolve", "vpn.example.test:18443:127.0.0.1", "--user", f"admin:{PASSWORD}", "-o", "runtime/downloaded-backup.tar.gz", f"https://vpn.example.test:18443/admin/backups/{filename}"])
        import tarfile
        with tarfile.open(runtime / "downloaded-backup.tar.gz") as archive:
            assert {".env", "data/control.token", "data/protocols.json"}.issubset(archive.getnames())
        print("PASS: dashboard service stop/start and asynchronous backup, service recovery and authenticated archive download", flush=True)
    finally:
        print(run(["sudo", "journalctl", "-u", "freenetvpn-control", "--no-pager", "-n", "50"], check=False).stdout, flush=True)
        run(["sudo", "systemctl", "stop", "freenetvpn-control"], check=False)
        logs = dc("logs", "--tail", "60", check=False)
        print(logs.stdout, flush=True)
        # Fixed disposable CI project only. The production installer never deletes volumes.
        dc("--profile", "wireguard", "--profile", "vless", "--profile", "test-client",
           "down", "--volumes", "--remove-orphans", check=False)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stdout, file=sys.stderr)
        print(error.stderr, file=sys.stderr)
        raise
