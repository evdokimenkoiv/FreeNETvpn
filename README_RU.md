# FreeNETvpn (РУС)

Развёртывание нескольких VPN одной командой на Ubuntu (22.04/24.04 LTS):
- IPsec IKEv2 (strongSwan, EAP-MSCHAPv2; собственный CA + сертификат сервера)
- L2TP/IPsec (xl2tpd + strongSwan)
- WireGuard (wg-easy)
- Outline (outline-server)
- VLESS (Xray-core через WebSocket + TLS за Caddy)
- Amnezia (официальный docker‑сервер, AmneziaWG)

**Единая панель**:
- CLI (`menu.sh`, EN/RU) — управление пользователями (WG, VLESS, IKEv2, L2TP), генерация профилей, бэкапы, диагностика.
- Web (`/admin`) за Caddy + Let’s Encrypt (prod), BasicAuth задаётся при установке.
- `/wg` — wg‑easy UI; `/outline` — локальные endpoints; `/docs` — справка.

## Быстрый старт
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/main/install.sh)
```

### Во время установки
- Язык, FQDN и e‑mail для LE
- Логин/пароль админ‑панели
- Сервисы (по умолчанию: **все**)
- IPv6: автоопределение (с вопросом)
- Порт WireGuard: 51820 / свой / случайный
- Усиление SSH: смена порта, запрет пароля, fail2ban и UFW
- **Опционально SSH 2FA (TOTP)** через Google Authenticator

### После установки
Откройте `https://<домен>/` → `/admin` и `/wg`, `/outline`, `/docs`.  
Для расширенных задач используйте `./menu.sh`.

## Устойчивость к блокировкам
- VLESS по **WS+TLS** со случайным путём (`VLESS_WS_PATH`) за Caddy — выглядит как обычный HTTPS.
- Скрипт `scripts/rotate_vless.sh` меняет UUID и путь.
- Поддержка split‑tunneling и выбора DNS на клиентах.

## Безопасность
- UFW + fail2ban. Опционально: смена порта SSH, запрет пароля, 2FA.
- **IKEv2** использует собственный CA и серверный сертификат (корректные расширения для IPsec).
- Веб‑панель — через TLS Caddy/LE (prod).

## Бэкапы и восстановление
- Бэкап через CLI или `/admin/backup` (архив для скачивания).
- Восстановление: `./restore.sh <backup.tar.gz>`.

## Лицензия
MIT
