# FreeNETvpn

One-command deploy of multiple VPN services on Ubuntu (22.04/24.04 LTS):
- IPsec IKEv2 (strongSwan)
- L2TP/IPsec (xl2tpd + strongSwan)
- WireGuard (wg-easy)
- Outline (outline-server)
- VLESS (Xray-core via WebSocket + TLS behind Caddy)
- Amnezia (official docker server, AmneziaWG)

**Unified control panel**:
- CLI panel (`menu.sh`) with multi-language (English/Russian).
- Web dashboard (`/admin`) served behind Caddy + Let's Encrypt (prod). Basic Auth is set during install.
- `/wg` exposes wg-easy UI; `/outline` — access to local Outline endpoints; `/docs` — local help.

## Quick start

> **Run on a fresh Ubuntu server with a public IP and DNS A/AAAA records pointing to your FQDN.**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/main/install.sh)
```

During install you will be asked for:
- Language (English/Russian)
- FQDN (e.g. `vpn.example.com`)
- E-mail for Let's Encrypt (prod)
- Admin username/password for the web panel
- Which services to install (default: **all**; you can deselect)
- IPv6: auto-detected, you can enable/disable explicitly
- WireGuard port: default 51820, choose custom or random allowed port
- SSH hardening (recommended): change SSH port, enable fail2ban & UFW (default on), optionally disable password logins

After completion open `https://<your-domain>/` to access the panel.


## Services & ports

- 80/tcp, 443/tcp — Caddy (auto TLS with Let’s Encrypt, production)
- 500/udp, 4500/udp — IPsec IKEv2/L2TP
- 1701/udp — L2TP
- 51820/udp — WireGuard (customizable/randomized)
- Additional internal ports are proxied by Caddy.

## Regional resilience (RU/CN focus)

- VLESS over **WebSocket+TLS** at a randomizable path (fronted by Caddy), indistinguishable from normal HTTPS.
- Ability to change paths/ports and regenerate VLESS/WG client files via menu.
- Split-tunneling and DNS options in clients.

## Backups & Restore

- From CLI panel you can **create a local backup** archive with configs/keys.
- Download the archive via web `/admin` page.
- Restore on a new server with: `restore.sh <backup.zip>`

## Disclaimer

- Use responsibly and according to your local laws. This project is for educational and administrative purposes.
- Strong defaults are provided, but you are responsible for security of your infrastructure.


