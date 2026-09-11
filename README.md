# FreeNETvpn v2.1

WireGuard (wg-easy 15.4.0), VLESS/WebSocket/gRPC/TLS (Xray 26.3.27), IKEv2, L2TP/IPsec, Outline and AmneziaWG, with an authenticated control panel behind Caddy 2.11.4. Ubuntu 22.04/24.04 LTS x86_64, Docker Compose v2, public IPv4.

All six protocol integrations are included. Existing installations are not overwritten; read [migration](docs/migration.md) and [protocol setup/client operations](docs/protocols.md). Amnezia integration means AmneziaWG with configuration export.

## Install

Create two DNS A records pointing directly at the server:
- `vpn.example.com` — panel and VLESS, also the WireGuard client endpoint.
- `wg.example.com` — protected wg-easy UI.

Allow TCP 80/443 and the selected [VPN ports](docs/protocols.md) in the hosting-provider firewall. Use working DNS and remove unusable AAAA records.

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

Open `https://vpn.example.com/admin` with username `admin` and the password you supplied. The responsive cabinet manages clients, service operations, downloads/QR codes, backups and an operation history. See the [cabinet and preset guide](docs/dashboard.md). VLESS and AmneziaWG each include three ready-made client presets.

For WireGuard, open `https://wg.example.com/`: first pass the same outer Basic Auth, then complete wg-easy's native setup. Create its native administrator account and set **endpoint = DOMAIN, port = WG_PORT**, DNS from .env. Create a client and import its QR/config. Two authentication layers protect the otherwise exposed first-run wizard. Changes to the UDP port must be made in both .env and the wg-easy UI.

Create a named VLESS client in the cabinet and choose WebSocket/TLS, mobile WebSocket, or gRPC/TLS. The original profile remains available; export it on the server:
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
`--services vless` or another comma-separated subset selects protocols on a new installation. All six are enabled by default. Existing installations retain their selection; use `sudo python3 tools/manage.py services all` and rerun the installer to enable the full bundle. `--password-stdin` supports a protected input stream; avoid putting passwords in command-line arguments or history.

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

Backups briefly stop running services, archive .env, runtime/ and data/, then resume the services even on failure. Archives contain secrets and private keys. Store them securely. The cabinet creates and downloads backups through an allowlisted local agent. The web container remains non-root/read-only and has no Docker socket or generic host-command API. A web restart may require signing in again; job results remain available.

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

GitHub Actions also runs Chromium desktop/mobile cabinet tests with an explicitly simulated API; screenshots are uploaded as artifacts. The real systemd agent, service operations, backup/download and all six client presets are exercised separately against Linux containers.

GitHub Actions runs actual TLS, WireGuard, Xray, IPsec/PPP, Outline and AmneziaWG client/server packet tests on Ubuntu 22.04 and 24.04. `tests/integration.py` and `tests/integration_extra.py` are for an **empty disposable Linux checkout only**; they create test projects and remove their Docker volumes afterwards. TLS clients explicitly trust test certificates. The Outline probe uses a disposable bridge with a non-private address range so Outline's RFC1918 destination filtering remains enabled.

Public CA issuance, external UDP, provider routing, DNS leaks, reboot/recovery and a full root installation on a VPS require [external acceptance](docs/acceptance.md). No blanket guarantee of availability through regional network filtering is made.

Spec Kit artifacts: [.specify/memory/constitution.md](.specify/memory/constitution.md), [specification](specs/001-reliable-core/spec.md), [plan](specs/001-reliable-core/plan.md), [tasks/evidence](specs/001-reliable-core/tasks.md).

Dashboard and presets: [specification](specs/003-dashboard-presets/spec.md), [plan](specs/003-dashboard-presets/plan.md), [tasks/evidence](specs/003-dashboard-presets/tasks.md).

All-protocol extension: [specification](specs/002-all-protocols/spec.md), [plan](specs/002-all-protocols/plan.md), [tasks/evidence](specs/002-all-protocols/tasks.md).

MIT for FreeNETvpn code; upstream components retain their respective licenses.
