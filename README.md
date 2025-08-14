# FreeNETvpn

One-command deploy of multiple VPN services on Ubuntu (22.04/24.04 LTS):
- IPsec IKEv2 (strongSwan, EAP-MSCHAPv2; own CA + server cert)
- L2TP/IPsec (xl2tpd + strongSwan)
- WireGuard (wg-easy)
- Outline (outline-server)
- VLESS (Xray-core via WebSocket + TLS behind Caddy)
- Amnezia (official docker server, AmneziaWG)

**Unified control panel**:
- CLI panel (`menu.sh`, EN/RU) – manage users (WG, VLESS, IKEv2, L2TP), generate profiles, backups, diagnostics.
- Web dashboard (`/admin`) behind Caddy + Let’s Encrypt (prod). Basic Auth set during install.
- `/wg` – wg-easy UI; `/outline` – local Outline endpoints; `/docs` – local help.

## Quick start

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/main/install.sh)
```

### During install
- Language (English/Russian)
- FQDN & email for Let’s Encrypt
- Admin login/password for web panel
- Services to install (**default: all**)
- IPv6: auto-detected (you can enable/disable explicitly)
- WireGuard port: default 51820, or custom, or random allowed
- SSH hardening: port change, disable password login, enable fail2ban & UFW (on by default)
- **Optional SSH 2FA (TOTP)** with Google Authenticator

### After install
Open `https://<your-domain>/` → `/admin` (BasicAuth) and `/wg`, `/outline`, `/docs`.  
Run `./menu.sh` for advanced tasks.

## Regional resilience (RU/CN focus)
- VLESS over **WebSocket+TLS** at randomized path (`VLESS_WS_PATH`), fronted by Caddy – looks like normal HTTPS.
- Scripts to rotate VLESS UUID & path (`scripts/rotate_vless.sh`).
- Split-tunneling & DNS options on clients.

## Security defaults
- UFW + fail2ban. SSH port randomization (optional). Password logins off (optional).  
- **IKEv2 uses own CA and server cert** (not Let’s Encrypt) – proper EKU/SAN for IPsec.  
- Web endpoints are TLS‑terminated via Caddy/LE (prod).

## Backups & Restore
- Create local backup via CLI or `/admin/backup`, download the archive.
- Restore on a new server: `./restore.sh <backup.tar.gz>`.

## License
MIT
