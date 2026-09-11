"""Optional VPN services: persistent credentials, configuration and client lifecycle."""
import base64
import json
import os
import plistlib
import re
import secrets
import ssl
import subprocess
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

import manage

EXTRA = {"ikev2", "l2tp", "outline", "amnezia"}


def command(*args, data=None):
    return subprocess.run(list(args), input=data, capture_output=True, check=True).stdout


def keypair():
    private = command("openssl", "genpkey", "-algorithm", "X25519", "-outform", "DER")
    public = command("openssl", "pkey", "-inform", "DER", "-pubout", "-outform", "DER", data=private)
    return {"private": base64.b64encode(private[-32:]).decode(), "public": base64.b64encode(public[-32:]).decode()}


def state_file(root):
    return root / "data/protocols.json"


def read_state(root):
    return json.loads(state_file(root).read_text())


def save(state, root):
    manage.atomic_write(state_file(root), json.dumps(state, indent=2) + "\n")


def certificate(root, domain):
    pki = root / "data/ipsec"
    for folder in ("private", "certs", "cacerts"):
        (pki / folder).mkdir(parents=True, exist_ok=True)
    ca, key = pki / "cacerts/ca.pem", pki / "private/ca.pem"
    if not ca.exists():
        if key.exists():
            raise ValueError("Incomplete IPsec CA: restore the matching certificate; key was preserved")
        command("openssl", "req", "-x509", "-newkey", "rsa:3072", "-nodes", "-days", "3650",
                "-subj", "/CN=FreeNETvpn IPsec CA", "-addext", "basicConstraints=critical,CA:TRUE",
                "-keyout", str(key), "-out", str(ca))
        os.chmod(key, 0o600)
    server = pki / "certs/server.pem"
    if not server.exists():
        csr = root / "runtime/server.csr"
        extension = root / "runtime/server.ext"
        manage.atomic_write(extension, f"subjectAltName=DNS:{domain}\nextendedKeyUsage=serverAuth\nkeyUsage=digitalSignature,keyEncipherment\n")
        command("openssl", "req", "-new", "-newkey", "rsa:3072", "-nodes", "-subj", f"/CN={domain}",
                "-keyout", str(pki / "private/server.pem"), "-out", str(csr))
        command("openssl", "x509", "-req", "-in", str(csr), "-CA", str(ca), "-CAkey", str(key),
                "-set_serial", str(secrets.randbits(128)), "-days", "825", "-extfile", str(extension), "-out", str(server))
        os.chmod(pki / "private/server.pem", 0o600)
        csr.unlink()
        extension.unlink()
    # A hostname change must never silently leave an invalid server identity.
    command("openssl", "x509", "-in", str(server), "-noout", "-checkhost", domain)


def prepare(config, root):
    config = manage.validate(config)
    enabled = set(config["COMPOSE_PROFILES"].split(","))
    if not enabled & EXTRA:
        return
    state = read_state(root) if state_file(root).exists() else {"version": 1, "clients": {"ikev2": {}, "l2tp": {}, "amnezia": {}}}
    if enabled & {"ikev2", "l2tp"}:
        state.setdefault("ipsec_psk", secrets.token_urlsafe(32))
        certificate(root, config["DOMAIN"])
    if "amnezia" in enabled and "awg" not in state:
        state["awg"] = {**keypair(), "params": {"Jc": 4, "Jmin": 40, "Jmax": 70, "S1": 16, "S2": 24,
            "S3": 16, "S4": 16, "H1": 10123456, "H2": 20123456, "H3": 30123456, "H4": 40123456}}
    if "outline" in enabled:
        state.setdefault("outline_prefix", secrets.token_urlsafe(32))
        path = root / "data/outline"
        path.mkdir(parents=True, exist_ok=True)
        if not (path / "api.crt").exists():
            command("openssl", "req", "-x509", "-newkey", "rsa:3072", "-nodes", "-days", "3650",
                    "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
                    "-keyout", str(path / "api.key"), "-out", str(path / "api.crt"))
            os.chmod(path / "api.key", 0o600)
        server_config = path / "shadowbox_server_config.json"
        current = json.loads(server_config.read_text()) if server_config.exists() else {}
        current.update(hostname=config["DOMAIN"], portForNewAccessKeys=int(config["OUTLINE_PORT"]))
        manage.atomic_write(server_config, json.dumps(current))
    save(state, root)
    render(config, root)


def render(config, root):
    enabled = set(config["COMPOSE_PROFILES"].split(","))
    manage.atomic_write(root / "runtime/ipsec.env", "ENABLE_L2TP=" + str("l2tp" in enabled).lower() + "\n")
    if not (root / "runtime/outline.env").exists():
        manage.atomic_write(root / "runtime/outline.env", "SB_API_PREFIX=unconfigured\n")
    if not state_file(root).exists():
        return
    state = read_state(root)
    path = root / "runtime/ipsec"
    if enabled & {"ikev2", "l2tp"} and "ipsec_psk" in state:
        path.mkdir(parents=True, exist_ok=True)
        common = "config setup\n  uniqueids=never\n\n"
        if "ikev2" in enabled:
            common += f"""conn ikev2
  keyexchange=ikev2
  auto=add
  left=%any
  leftid=@{config['DOMAIN']}
  leftcert=server.pem
  leftauth=pubkey
  leftsendcert=always
  leftsubnet=0.0.0.0/0
  right=%any
  rightauth=eap-mschapv2
  rightsourceip=10.99.0.10-10.99.0.250
  rightdns={config['DNS1']},{config['DNS2']}
  eap_identity=%identity
  fragmentation=yes
  forceencaps=yes
  dpdaction=clear
  dpddelay=30s
  rekey=no
  ike=aes256-sha256-modp2048,aes128-sha256-modp2048!
  esp=aes256-sha256,aes128-sha256!

"""
        if "l2tp" in enabled:
            common += """conn l2tp
  keyexchange=ikev1
  auto=add
  type=transport
  authby=secret
  left=%any
  leftprotoport=17/1701
  right=%any
  rightprotoport=17/%any
  forceencaps=yes
  dpdaction=clear
  dpddelay=30s
  rekey=no
  ike=aes256-sha256-modp2048,aes256-sha1-modp2048,aes128-sha1-modp1024!
  esp=aes256-sha256,aes256-sha1,aes128-sha1!
"""
        manage.atomic_write(path / "ipsec.conf", common)
        secret = ': RSA server.pem\n' + (f': PSK "{state["ipsec_psk"]}"\n' if "l2tp" in enabled else "")
        secret += "".join(f'{name} : EAP "{value["password"]}"\n' for name, value in state["clients"]["ikev2"].items())
        manage.atomic_write(path / "ipsec.secrets", secret)
        manage.atomic_write(path / "chap-secrets", "".join(f'{name} l2tpd "{v["password"]}" *\n' for name,v in state["clients"]["l2tp"].items()))
        manage.atomic_write(path / "xl2tpd.conf", "[global]\nport = 1701\naccess control = no\n[lns default]\nip range = 10.99.1.10-10.99.1.250\nlocal ip = 10.99.1.1\nrequire chap = yes\nrefuse pap = yes\nrequire authentication = yes\nname = l2tpd\npppoptfile = /etc/ppp/options.xl2tpd\nlength bit = yes\n")
        manage.atomic_write(path / "options.xl2tpd", f"require-mschap-v2\nrefuse-pap\nrefuse-chap\nrefuse-mschap\nname l2tpd\nms-dns {config['DNS1']}\nms-dns {config['DNS2']}\nauth\nmtu 1280\nmru 1280\nlock\nnodefaultroute\nlcp-echo-failure 4\nlcp-echo-interval 30\n")
    if "amnezia" in enabled and "awg" in state:
        awg = state["awg"]
        text = f'[Interface]\nPrivateKey = {awg["private"]}\nListenPort = {config["AWG_PORT"]}\n'
        text += "".join(f"{key} = {value}\n" for key,value in awg["params"].items())
        for peer in state["clients"]["amnezia"].values():
            text += f'\n[Peer]\nPublicKey = {peer["public"]}\nAllowedIPs = {peer["address"]}/32\n'
        manage.atomic_write(root / "runtime/amnezia/awg0.conf", text)
    if "outline" in enabled and "outline_prefix" in state:
        manage.atomic_write(root / "runtime/outline.env", f'SB_API_PREFIX={state["outline_prefix"]}\n')


def outline_api(config, root, path, method="GET", body=None):
    state = read_state(root)
    context = ssl.create_default_context(cafile=str(root / "data/outline/api.crt"))
    request = Request(f'https://127.0.0.1:{config["OUTLINE_API_PORT"]}/{state["outline_prefix"]}/{path}',
                      method=method, data=None if body is None else json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, context=context, timeout=15) as response:
        data = response.read()
        return json.loads(data) if data else {}


def export_client(protocol, name, config, state, root):
    folder = root / "data/exports" / protocol
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    if protocol == "outline":
        matches = [c for c in outline_api(config, root, "access-keys")["accessKeys"] if c.get("name") == name]
        if len(matches) != 1:
            raise ValueError("Outline client name missing or ambiguous")
        path = folder / f"{name}.txt"
        manage.atomic_write(path, matches[0]["accessUrl"] + "\n")
    else:
        peer = state["clients"][protocol][name]
        if protocol == "amnezia":
            awg = state["awg"]
            content = f'[Interface]\nPrivateKey = {peer["private"]}\nAddress = {peer["address"]}/32\nDNS = {config["DNS1"]}, {config["DNS2"]}\nMTU = 1280\n'
            content += "".join(f"{k} = {v}\n" for k,v in awg["params"].items())
            content += f'\n[Peer]\nPublicKey = {awg["public"]}\nAllowedIPs = 0.0.0.0/0\nEndpoint = {config["DOMAIN"]}:{config["AWG_PORT"]}\nPersistentKeepalive = 25\n'
            path = folder / f"{name}.conf"
            manage.atomic_write(path, content)
        else:
            values = dict(server=config["DOMAIN"], username=name, password=peer["password"], protocol=protocol)
            if protocol == "l2tp":
                values["ipsec_psk"] = state["ipsec_psk"]
            else:
                values["remote_id"] = config["DOMAIN"]
                manage.atomic_write(folder / "ca.pem", (root / "data/ipsec/cacerts/ca.pem").read_text())
                ca_uuid = str(uuid.uuid4())
                def payload(kind, extra):
                    return dict(PayloadType=kind, PayloadVersion=1, PayloadIdentifier=str(uuid.uuid4()), PayloadUUID=str(uuid.uuid4()), PayloadDisplayName="FreeNETvpn", **extra)
                cert = ssl.PEM_cert_to_DER_cert((folder / "ca.pem").read_text())
                ca_payload = payload("com.apple.security.root", {"PayloadContent": cert})
                ca_payload["PayloadUUID"] = ca_uuid
                vpn = payload("com.apple.vpn.managed", {"UserDefinedName": f"FreeNETvpn {name}", "VPNType": "IKEv2", "IKEv2": {
                    "RemoteAddress": config["DOMAIN"], "RemoteIdentifier": config["DOMAIN"], "AuthenticationMethod": "None",
                    "ExtendedAuthEnabled": 1, "AuthName": name, "AuthPassword": peer["password"], "PayloadCertificateUUID": ca_uuid}})
                profile = payload("Configuration", {"PayloadContent": [ca_payload, vpn]})
                manage.atomic_write(folder / f"{name}.mobileconfig", plistlib.dumps(profile).decode())
            path = folder / f"{name}.json"
            manage.atomic_write(path, json.dumps(values, indent=2) + "\n")
    return path


def client(action, protocol, name, root):
    config = manage.read_config(root)
    if protocol not in config["COMPOSE_PROFILES"].split(","):
        raise ValueError(f"{protocol} is not enabled")
    if action != "list" and (not name or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", name)):
        raise ValueError("Client name must have 1-32 letters, digits, underscores or hyphens")
    state = read_state(root)
    if protocol == "outline":
        peers = outline_api(config, root, "access-keys")["accessKeys"]
        selected = [p for p in peers if p.get("name") == name]
        if action == "list":
            print(json.dumps([{"name": p.get("name"), "id": p["id"]} for p in peers])); return
        if action == "add":
            if selected:
                raise ValueError("Client already exists")
            added = outline_api(config, root, "access-keys", "POST", {"name": name, "port": int(config["OUTLINE_PORT"])})
            # Explicit rename also supports server releases that ignore POST's name.
            outline_api(config, root, f'access-keys/{added["id"]}/name', "PUT", {"name": name})
        elif action == "revoke":
            if len(selected) != 1:
                raise ValueError("Client missing or ambiguous")
            outline_api(config, root, f'access-keys/{selected[0]["id"]}', "DELETE")
    else:
        peers = state["clients"][protocol]
        if action == "list":
            print(json.dumps(sorted(peers))); return
        if action == "add":
            if name in peers:
                raise ValueError("Client already exists; use export")
            if protocol == "amnezia":
                used = {v["address"] for v in peers.values()}
                address = next((f"10.98.0.{i}" for i in range(2,251) if f"10.98.0.{i}" not in used), None)
                if not address:
                    raise ValueError("Client address pool exhausted")
                peers[name] = {**keypair(), "address": address}
            else:
                peers[name] = {"password": secrets.token_urlsafe(24)}
        elif name not in peers:
            raise ValueError("Client does not exist")
        elif action == "revoke":
            del peers[name]
        if action in {"add", "revoke"}:
            save(state, root)
            render(config, root)
            # Recreate closes existing sessions after revocation and refreshes bind mounts.
            service = "amnezia" if protocol == "amnezia" else "ipsec"
            manage.compose(["up", "-d", "--force-recreate", "--wait", service], root)
    if action == "revoke":
        for path in (root / "data/exports" / protocol).glob(f"{name}.*"):
            path.unlink()
        print("Client revoked")
    else:
        print(export_client(protocol, name, config, state, root))
