"""Real IPsec/L2TP, Outline and AmneziaWG traffic in a disposable Linux checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import manage
import protocols

ENV = dict(os.environ, COMPOSE_PROFILES="ikev2,l2tp,outline,amnezia")
BASE = ["docker", "compose", "-p", "freenet-extra", "--env-file", ".env", "-f", "docker-compose.yml", "-f", "runtime/extra.yml"]


def run(args, check=True):
    return subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True, text=True, check=check)


def dc(*args, check=True):
    return run(BASE + list(args), check)


def address(service):
    ident = dc("ps", "-q", service).stdout.strip()
    return run(["docker", "inspect", "-f", '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', ident]).stdout.strip()


def eventually(action, seconds=40):
    last = None
    for _ in range(seconds):
        try:
            return action()
        except (subprocess.CalledProcessError, OSError, AssertionError) as error:
            last = error
            time.sleep(1)
    raise last


def write(path, content):
    file = ROOT / "runtime" / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)
    return file


def start_ipsec_client(service, config, secret):
    write(f"{service}/ipsec.conf", config)
    write(f"{service}/ipsec.secrets", secret)
    dc("up", "-d", service)
    dc("exec", "-T", service, "sh", "-c", "cp /client/ipsec.conf /etc/ipsec.conf; cp /client/ipsec.secrets /etc/ipsec.secrets; cp /ca/ca.pem /etc/ipsec.d/cacerts/ca.pem; ipsec start")
    eventually(lambda: dc("exec", "-T", service, "ipsec", "up", "probe"))
    def installed():
        status = dc("exec", "-T", service, "ipsec", "statusall").stdout
        assert "INSTALLED" in status, status
    eventually(installed)


def main():
    if (ROOT / ".env").exists() or (ROOT / "data").exists():
        raise RuntimeError("Requires empty disposable checkout")
    config = dict(CONFIG_VERSION="2", DOMAIN="vpn.example.test", WG_DOMAIN="wg.example.test", LE_EMAIL="ci@example.test",
        ADMIN_USER="admin", ADMIN_PASSWORD_HASH=manage.password_hash("CI-only-long-password"), WG_PORT="52999",
        DNS1="1.1.1.1", DNS2="8.8.8.8", COMPOSE_PROFILES=ENV["COMPOSE_PROFILES"],
        VLESS_UUID="9ab3b0aa-4a2b-44b7-acd4-5a644eec3c89", VLESS_WS_PATH="/assets-ci-extra")
    config = manage.validate(config)
    manage.write_config(config)
    manage.render(config)
    protocols.prepare(config, ROOT)
    state = protocols.read_state(ROOT)
    state["clients"]["ikev2"]["testclient"] = {"password": "IKE-ci-password-987654321"}
    state["clients"]["l2tp"]["testclient"] = {"password": "L2TP-ci-password-987654321"}
    state["clients"]["amnezia"]["testclient"] = {**protocols.keypair(), "address": "10.98.0.2"}
    protocols.save(state, ROOT)
    protocols.render(config, ROOT)
    before = (ROOT / "data/protocols.json").read_bytes()
    protocols.prepare(config, ROOT)
    assert before == (ROOT / "data/protocols.json").read_bytes()
    write("echo/probe.txt", "freenet-extra-tunnel-ok")
    write("extra.yml", '''services:
  echo-server:
    image: python:3.12-slim
    command: [python, -m, http.server, "18080", --bind, 0.0.0.0]
    working_dir: /srv
    volumes: ["./runtime/echo:/srv:ro"]
    networks: [backend]
  ike-client:
    build: ./services/ipsec
    profiles: [test-client]
    entrypoint: [sleep, infinity]
    cap_add: [NET_ADMIN]
    volumes: ["./runtime/ike-client:/client:ro", "./data/ipsec/cacerts:/ca:ro"]
    networks: [backend]
  l2tp-client:
    build: ./services/ipsec
    profiles: [test-client]
    entrypoint: [sleep, infinity]
    cap_add: [NET_ADMIN]
    devices: [/dev/ppp:/dev/ppp]
    volumes: ["./runtime/l2tp-client:/client:ro", "./data/ipsec/cacerts:/ca:ro"]
    networks: [backend]
  outline-client:
    image: ghcr.io/xtls/xray-core:26.3.27
    profiles: [test-client]
    command: [run, -config, /client.json]
    ports: ["127.0.0.1:11081:1080"]
    volumes: ["./runtime/outline-client.json:/client.json:ro"]
    networks: [backend]
  awg-client:
    build: ./services/amnezia
    profiles: [test-client]
    cap_add: [NET_ADMIN]
    devices: [/dev/net/tun:/dev/net/tun]
    environment: {AWG_CLIENT: "true", AWG_ADDRESS: "10.98.0.2/32"}
    volumes: ["./runtime/awg-client:/config:ro"]
    networks: [backend]
networks:
  backend:
    # Outline intentionally rejects RFC1918 destinations. This disposable bridge
    # uses a non-private range so the real server's destination policy stays on.
    ipam:
      config: [{subnet: "11.254.239.0/24"}]
''')
    try:
        dc("up", "-d", "--build", "--wait", "--wait-timeout", "180", "ipsec", "outline", "amnezia", "echo-server")
        echo_ip, ipsec_ip = address("echo-server"), address("ipsec")
        url = f"http://{echo_ip}:18080/probe.txt"
        # IKEv2: server certificate checked against our CA, EAP login, assigned VIP.
        start_ipsec_client("ike-client", f'''config setup
conn probe
  auto=add
  keyexchange=ikev2
  left=%defaultroute
  leftid=testclient
  leftauth=eap-mschapv2
  eap_identity=testclient
  leftsourceip=%config
  right={ipsec_ip}
  rightid=@{config['DOMAIN']}
  rightauth=pubkey
  rightsubnet={echo_ip}/32
  forceencaps=yes
  ike=aes256-sha256-modp2048!
  esp=aes256-sha256!
''', 'testclient : EAP "IKE-ci-password-987654321"\n')
        addresses = json.loads(dc("exec", "-T", "ike-client", "ip", "-j", "-4", "address", "show").stdout)
        vip = next(a["local"] for iface in addresses for a in iface["addr_info"] if a["local"].startswith("10.99.0."))
        payload = dc("exec", "-T", "ike-client", "curl", "-fsS", "--max-time", "20", "--interface", vip, url)
        assert payload.stdout == "freenet-extra-tunnel-ok"
        assert "INSTALLED" in dc("exec", "-T", "ike-client", "ipsec", "statusall").stdout
        print("PASS: IKEv2 certificate validation, EAP login, CHILD_SA and HTTP through IPsec", flush=True)
        # L2TP client starts only after its IKEv1 transport SA is established.
        start_ipsec_client("l2tp-client", f'''config setup
conn probe
  auto=add
  keyexchange=ikev1
  type=transport
  authby=secret
  left=%defaultroute
  leftprotoport=17/1701
  right={ipsec_ip}
  rightprotoport=17/1701
  forceencaps=yes
  ike=aes256-sha256-modp2048!
  esp=aes256-sha256!
''', f': PSK "{state["ipsec_psk"]}"\n')
        write("l2tp-client/xl2tpd.conf", f"[global]\nport = 1701\nforce userspace = yes\n[lac vpn]\nlns = {ipsec_ip}\npppoptfile = /client/options\nlength bit = yes\n")
        write("l2tp-client/options", 'name testclient\npassword L2TP-ci-password-987654321\nnoauth\nrefuse-eap\nnoccp\nnoipdefault\nipcp-accept-local\nipcp-accept-remote\nmtu 1280\nmru 1280\n')
        dc("exec", "-T", "l2tp-client", "sh", "-c", "mkdir -p /run/xl2tpd; xl2tpd -c /client/xl2tpd.conf; sleep 1; echo 'c vpn' > /run/xl2tpd/l2tp-control")
        eventually(lambda: dc("exec", "-T", "l2tp-client", "ip", "address", "show", "ppp0"))
        dc("exec", "-T", "l2tp-client", "ip", "route", "add", echo_ip + "/32", "dev", "ppp0")
        payload = dc("exec", "-T", "l2tp-client", "curl", "-fsS", "--max-time", "20", "--interface", "ppp0", url)
        assert payload.stdout == "freenet-extra-tunnel-ok"
        print("PASS: L2TP/IPsec transport SA, MSCHAPv2/PPP and HTTP through ppp0", flush=True)
        # Outline's management endpoint verifies its pinned certificate on loopback.
        eventually(lambda: protocols.outline_api(config, ROOT, "access-keys"))
        protocols.client("add", "outline", "testclient", ROOT)
        peer = protocols.outline_api(config, ROOT, "access-keys")["accessKeys"][0]
        write("outline-client.json", json.dumps({"inbounds": [{"listen": "0.0.0.0", "port": 1080, "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [{"protocol": "shadowsocks", "settings": {"servers": [{"address": "outline", "port": peer["port"], "method": peer["method"], "password": peer["password"]}]}}]}))
        dc("up", "-d", "outline-client")
        payload = eventually(lambda: run(["curl", "-fsS", "--max-time", "10", "--socks5-hostname", "127.0.0.1:11081", url]))
        assert payload.stdout == "freenet-extra-tunnel-ok"
        protocols.client("revoke", "outline", "testclient", ROOT)
        assert not protocols.outline_api(config, ROOT, "access-keys")["accessKeys"]
        print("PASS: Outline API TLS, create/export key, real Shadowsocks payload and key revocation", flush=True)
        # AWG: both ends use upstream AmneziaWG and non-default packet parameters.
        exported = protocols.export_client("amnezia", "testclient", config, state, ROOT).read_text()
        lines = [line for line in exported.splitlines() if not line.startswith(("Address =", "DNS =", "MTU ="))]
        awg_conf = "\n".join(lines).replace(config["DOMAIN"], address("amnezia")) + "\n"
        write("awg-client/awg0.conf", awg_conf)
        dc("up", "-d", "--build", "--wait", "awg-client")
        dc("exec", "-T", "awg-client", "ip", "route", "add", echo_ip + "/32", "dev", "awg0")
        payload = dc("exec", "-T", "awg-client", "curl", "-fsS", "--max-time", "20", "--interface", "awg0", url)
        assert payload.stdout == "freenet-extra-tunnel-ok"
        assert any(int(x.split()[1]) for x in dc("exec", "-T", "awg-client", "awg", "show", "awg0", "latest-handshakes").stdout.splitlines())
        print("PASS: AmneziaWG obfuscated handshake and HTTP through awg0", flush=True)
    finally:
        print(dc("logs", "--tail", "80", check=False).stdout, flush=True)
        dc("--profile", "*", "down", "--volumes", "--remove-orphans", check=False)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stdout, file=sys.stderr)
        print(error.stderr, file=sys.stderr)
        raise
