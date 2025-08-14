![CI](https://github.com/evdokimenkoiv/FreeNETvpn/actions/workflows/ci.yml/badge.svg)

# FreeNETvpn (РУС)

Развёртывание нескольких VPN одной командой на Ubuntu (22.04/24.04 LTS):
- IPsec IKEv2 (strongSwan, EAP-MSCHAPv2; собственный CA + серверный сертификат)
- L2TP/IPsec (xl2tpd + strongSwan)
- WireGuard (wg-easy)
- Outline (outline-server)
- VLESS (Xray-core через WebSocket + TLS за Caddy)
- Amnezia (официальный docker‑сервер, AmneziaWG)

**Единая панель**:
- CLI (`menu.sh`, EN/RU) — управление пользователями (WG, VLESS, IKEv2, L2TP), профили, бэкапы, диагностика.
- Web (`/admin`) за Caddy + Let’s Encrypt (prod).

## Быстрый старт
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/main/install.sh)
```

## CI и Health Check
- CI: Shellcheck, YAML‑lint, сборка admin‑образа, проверка compose, **проверка переменных окружения**, **сборка релиз-артефакта**.
- На сервере:
```
sudo bash scripts/health_check.sh
sudo bash scripts/health_check.sh -q
```

## Лицензия
MIT
