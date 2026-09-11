# FreeNETvpn v2.1

WireGuard (wg-easy 15.4.0), VLESS/WebSocket/gRPC/TLS (Xray 26.3.27), IKEv2, L2TP/IPsec, Outline and AmneziaWG, with an authenticated control panel behind Caddy 2.11.4. Ubuntu 22.04/24.04/26.04 LTS x86_64, Docker Compose plugin, public IPv4.

All six protocol integrations are included. Existing installations are not overwritten; read [migration](docs/migration.md) and [protocol setup/client operations](docs/protocols.md). Amnezia integration means AmneziaWG with configuration export.

## Быстрое развёртывание

Текущая версия находится в [PR #1](https://github.com/evdokimenkoiv/FreeNETvpn/pull/1), ветка `codex/freenetvpn-reliability`. До слияния **не используйте `main` для новой установки этой версии**.

Нужна Ubuntu **22.04/24.04/26.04 LTS x86_64** с systemd, публичным IPv4 и доступом sudo. Создайте два DNS A-записи (`vpn.example.com` и `wg.example.com`) на IP сервера. Откройте у провайдера TCP 80/443 и [порты выбранных VPN](docs/protocols.md); уберите неработающие AAAA-записи.

Одна команда на чистом сервере устанавливает загрузчик, получает полный проект в `/opt/freenetvpn` и запускает интерактивное развёртывание:

```bash
sudo bash -c 'set -e; apt-get update -qq; apt-get install -y ca-certificates curl; export FREENET_REF=codex/freenetvpn-reliability; f=$(mktemp); trap "rm -f -- \"$f\"" EXIT; curl -fsSL "https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/${FREENET_REF}/install.sh" -o "$f"; bash "$f"'
```

Установщик спросит два домена, email для сертификата и пароль администратора (16+ символов). Сам установит Docker/Compose, подготовит шесть протоколов, кабинет и systemd-агент, проверит конфигурацию, HTTPS и защиту входа. DNS и firewall провайдера настраиваются заранее. Мастер WireGuard завершается после установки в браузере.

Если полный проект уже скачан, единая команда из его каталога:

```bash
sudo bash install.sh
```

`sudo bash install.sh --existing` повторно применяет существующую конфигурацию; `--no-firewall` оставляет управление UFW оператору. Установщик сохраняет обнаруженные SSH-порты и **не меняет настройки SSH**. `bash install.sh --help` доступен без sudo и ничего не устанавливает.

Повторный запуск загрузчика использует найденную установку и не обновляет её код автоматически. Для обновления Git- и архивной установок смотрите [инструкцию развёртывания и обновления](docs/deployment.md). Ошибка загрузки не оставляет частично установленный проект: повторите ту же команду.

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

Оценка Spec Kit и прослеживаемость требований: [assessment](docs/spec-kit-assessment.md), [матрица требований и проверок](docs/traceability.md).

Spec Kit artifacts: [.specify/memory/constitution.md](.specify/memory/constitution.md), [specification](specs/001-reliable-core/spec.md), [plan](specs/001-reliable-core/plan.md), [tasks/evidence](specs/001-reliable-core/tasks.md).

Dashboard and presets: [specification](specs/003-dashboard-presets/spec.md), [plan](specs/003-dashboard-presets/plan.md), [tasks/evidence](specs/003-dashboard-presets/tasks.md).

All-protocol extension: [specification](specs/002-all-protocols/spec.md), [plan](specs/002-all-protocols/plan.md), [tasks/evidence](specs/002-all-protocols/tasks.md).

MIT for FreeNETvpn code; upstream components retain their respective licenses.

Official Spec Kit 1.0.6 workflow: [setup and agent commands](docs/spec-kit.md), [agent review evidence](docs/spec-kit-review.md), [integration specification](specs/004-spec-kit-integration/spec.md). Run `python tools/spec_audit.py` for the offline structural audit; it does not replace semantic agent review or packet tests. CI checks official context helpers on Ubuntu and Windows.
