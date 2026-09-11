# FreeNETvpn v2

WireGuard (wg-easy 15.4.0), VLESS over WebSocket + TLS (Xray 26.3.27), and an authenticated control panel behind Caddy 2.11.4. Ubuntu 22.04/24.04 LTS, Docker Compose v2, public IPv4.

**Scope:** v2 restores WireGuard and VLESS. IKEv2/L2TP, Outline and Amnezia from the original repository are retained as legacy reference and are not claimed to work. Existing installations are not overwritten; read [migration](docs/migration.md).

## Install

Create two DNS A records pointing directly at the server:
- `vpn.example.com` — panel and VLESS, also the WireGuard client endpoint.
- `wg.example.com` — protected wg-easy UI.

Allow TCP 80/443 and your chosen WireGuard UDP port (default 51820) in the hosting-provider firewall. Use working DNS and remove unusable AAAA records.

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/evdokimenkoiv/FreeNETvpn.git
cd FreeNETvpn
sudo bash install.sh
```

The installer asks for both domains, a certificate email and a password (16+ characters). It preserves detected SSH ports before enabling UFW and **does not change SSH settings**. To manage your firewall yourself, use `--no-firewall`. It validates generated configurations and waits for HTTPS/authentication checks; a failure returns nonzero.

The downloadable entry point also fetches a complete checkout (not just a shell file):
```bash
curl -fsSL https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/main/install.sh -o /tmp/freenet-install.sh
sudo bash /tmp/freenet-install.sh
```
Defaults to /opt/freenetvpn; an existing target directory without a v2 project is refused.

## First connection

Open `https://vpn.example.com/admin` with username `admin` and the password you supplied.

For WireGuard, open `https://wg.example.com/`: first pass the same outer Basic Auth, then complete wg-easy's native setup. Create its native administrator account and set **endpoint = DOMAIN, port = WG_PORT**, DNS from .env. Create a client and import its QR/config. Two authentication layers protect the otherwise exposed first-run wizard. Changes to the UDP port must be made in both .env and the wg-easy UI.

Export VLESS on the server:
```bash
sudo python3 tools/manage.py vless-uri
```
The URI contains credentials: share privately. Certificate validation stays enabled. A connected process or healthy UI is not proof of external VPN traffic; complete [acceptance checks](docs/acceptance.md).

## Configuration and updates

Python 3.10+ is sufficient for the management scripts; the panel uses Python 3.12 in Docker. No Python packages are required on the host.

`.env` is validated as data, never executed. The configure command creates unique credentials and renders runtime/admin.json, runtime/xray.json and runtime/Caddyfile. Passwords are PBKDF2 hashes. Runtime files, keys and data are Git-ignored. Invalid or old-format configuration fails without being overwritten.

For automation:
```bash
sudo python3 tools/manage.py configure --domain vpn.example.com --wg-domain wg.example.com --email admin@example.com --wg-port 51820
sudo bash install.sh --existing
```
`--services vless` or `--services wireguard` selects one protocol. Both are enabled by default. `--password-stdin` supports a protected input stream; avoid putting passwords in command-line arguments or history.

For an existing v2 installation, create a backup, update the checkout to a reviewed commit, and run:
```bash
sudo bash scripts/backup.sh
sudo bash install.sh --existing
```
This validates and re-renders existing values and recreates containers to refresh bind-mounted configuration; credentials and data remain. No automatic migration from old named volumes is performed.

## Operations

```bash
sudo bash menu.sh
sudo bash scripts/health_check.sh
sudo bash scripts/diagnostics.sh
sudo bash scripts/backup.sh
sudo bash scripts/rotate_vless.sh --confirm
```

Rotation creates a backup, changes UUID/path, validates Xray/Caddy and recreates them. Validation/start errors restore old settings. Existing VLESS clients need the newly exported profile.

Backups briefly stop running services, archive .env, runtime/ and data/, then resume the services even on failure. Archives contain secrets and private keys. Store them securely. The read-only web panel lists/downloads completed backups; it cannot execute Docker or host commands.

Restore to an **empty v2 installation**:
```bash
sudo bash restore.sh /secure/location/freenetvpn-TIMESTAMP.tar.gz
sudo bash install.sh --existing
```
Restore validates all archive entries before extracting, rejects links/traversal and refuses existing configuration/data. Old incomplete v1 archives are not accepted.

## Verification

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
shellcheck -S warning -e SC1091 install.sh menu.sh restore.sh scripts/*.sh
```

GitHub Actions also runs actual Caddy/TLS, Xray client/server and kernel WireGuard packet tests on Ubuntu 22.04 and 24.04. `tests/integration.py` is for an **empty disposable Linux checkout only**; it creates a test project and removes its Docker volumes afterwards. It uses a private test CA with explicit certificate validation.

Public CA issuance, external UDP, provider routing, DNS leaks, reboot/recovery and a full root installation on a VPS require [external acceptance](docs/acceptance.md). No blanket guarantee of availability through regional network filtering is made.

Spec Kit artifacts: [.specify/memory/constitution.md](.specify/memory/constitution.md), [specification](specs/001-reliable-core/spec.md), [plan](specs/001-reliable-core/plan.md), [tasks/evidence](specs/001-reliable-core/tasks.md).

MIT for FreeNETvpn code; upstream components retain their respective licenses.
