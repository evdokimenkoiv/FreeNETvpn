# All six protocols

New installations enable WireGuard, VLESS, IKEv2, L2TP/IPsec, Outline and AmneziaWG. Ubuntu 22.04/24.04 x86_64 is the baseline for the complete bundle. The pinned official Outline image is x86_64; select a subset without Outline on other architectures and validate that platform separately.

## Enable protocols on an existing v2 installation

Update to this reviewed version, then:

```bash
sudo python3 tools/manage.py services all
sudo bash install.sh --existing
```

`services` creates a backup before changing the selection. Supply a comma-separated subset instead of `all` to select protocols. An existing `.env` is not silently changed by the installer. Old v2 files without the new port keys use the defaults below. Keys and clients persist under `data/` and are included in backups. Enabling services does not import old host IPsec accounts or third-party Docker volumes.

| Protocol | Public ports | Client |
| --- | --- | --- |
| WireGuard | WG_PORT UDP, default 51820 | WireGuard / wg-easy QR |
| VLESS/WebSocket/TLS | 443 TCP | Compatible VLESS client |
| IKEv2 | 500/4500 UDP | IKEv2 EAP-MSCHAPv2 with imported CA |
| L2TP/IPsec | 500/4500 UDP | L2TP/IPsec PSK + MSCHAPv2 |
| Outline | OUTLINE_PORT TCP/UDP, default 2443 | Outline access key |
| AmneziaWG | AWG_PORT UDP, default 51830 | Compatible AmneziaWG configuration client |

TCP 80/443 is also needed for Caddy HTTPS. Outline's management port (`OUTLINE_API_PORT`, default 19090) binds only to 127.0.0.1 and must stay private. The CLI validates its self-signed API certificate explicitly. UDP 1701 is not published; the IPsec container drops L2TP packets without an IPsec policy. Configure the provider firewall as well as host rules.

## Client operations

Use `sudo bash menu.sh` → 7, or:

```bash
sudo python3 tools/manage.py client add ikev2 phone
sudo python3 tools/manage.py client add l2tp laptop
sudo python3 tools/manage.py client add outline tablet
sudo python3 tools/manage.py client add amnezia travel
sudo python3 tools/manage.py client list amnezia
sudo python3 tools/manage.py client export amnezia travel
sudo python3 tools/manage.py client revoke amnezia travel
```

`add` creates unique credentials, rejects duplicate names and prints the export file path. `export` preserves credentials. `revoke` removes the peer/account/key and its local export; IPsec/Amnezia recreation closes existing sessions and briefly interrupts other clients of that service. If recreation fails, the command fails; rerun `install.sh --existing` to apply the saved state. Keep exports private: they contain passwords or private keys.

- **IKEv2:** `data/exports/ikev2/NAME.json` has server, remote ID, username/password; `ca.pem` is the server CA. Trust this CA in the VPN client, verify remote ID equals DOMAIN, and select EAP-MSCHAPv2. `NAME.mobileconfig` provides an Apple profile, including credentials and CA; platform import still requires operator validation. The initial CA is retained. A DOMAIN change requires deliberate certificate migration; the installer refuses a mismatched existing certificate.
- **L2TP/IPsec:** `data/exports/l2tp/NAME.json` has server, PSK and PPP username/password. PSK is shared across this service; client passwords are unique. Uses IKEv1 for compatibility and is not offered by every current mobile OS. Windows behind NAT may require its native IPsec NAT-T policy setting. Prefer IKEv2 when multiple clients share one NAT. xl2tpd uses userspace L2TP with standard PPP modules.
- **Outline:** `data/exports/outline/NAME.txt` contains the `ss://` key for Outline. Management is through the CLI, not an exposed Outline Manager API. Keep the configured data port stable once keys exist; changing it requires replacing existing keys and updating firewall mappings.
- **AmneziaWG:** `data/exports/amnezia/NAME.conf` includes matching packet obfuscation parameters. Import into an AmneziaWG configuration-compatible client. This is the AmneziaWG protocol, not the Amnezia desktop application's complete SSH/Docker management system. Builds use official AmneziaWG Go v3.1.20260828 and tools v3.1.20260812 commits; no custom host kernel module is installed.

The original shell helper names for IKEv2/L2TP now call the managed v2 CLI. Originals remain in `legacy/` only as historical reference.

## Verification and recovery

`sudo bash scripts/health_check.sh` checks configured containers, public HTTPS/authentication, the IPsec/AWG daemons and Outline API TLS. These checks do not prove off-server connectivity. Connect each client from a different network, verify HTTP/HTTPS egress and DNS, test wrong credentials and revocation, and repeat after reboot.

Backups include protocol credentials, IPsec CA/server keys, Outline API certificate/state and all exported clients. Restore only into an empty installation, then run `install.sh --existing`. Check protocol state and clients after restore. See [acceptance](acceptance.md) and [migration](migration.md).
