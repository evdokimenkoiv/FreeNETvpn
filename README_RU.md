# FreeNETvpn v2

Рабочее ядро для **WireGuard и VLESS/WebSocket/TLS** на Ubuntu 22.04/24.04. Панель защищена авторизацией, SSH-настройки установщик не меняет, повторный запуск сохраняет ключи.

**IKEv2/L2TP, Outline и Amnezia в этой версии не восстановлены.** Их исходные материалы сохранены в legacy/. Старые установки и Docker-тома автоматически не переносятся: [порядок миграции](docs/migration.md).

## Запуск

Подготовьте два DNS-имени на публичный IPv4 сервера: например vpn.example.com и wg.example.com. Разрешите TCP 80/443 и UDP-порт WireGuard в firewall провайдера.

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/evdokimenkoiv/FreeNETvpn.git
cd FreeNETvpn
sudo bash install.sh
```

Укажите два домена, почту и пароль длиной от 16 символов. Панель — https://vpn.example.com/admin, логин admin. Перед включением UFW сохраняются разрешения для обнаруженных SSH-портов. Параметр --no-firewall оставляет управление firewall вам.

На https://wg.example.com/ пройдите внешнюю Basic Auth и мастер wg-easy: создайте его внутренний аккаунт, задайте адрес DOMAIN, порт WG_PORT и DNS из .env. Затем создайте клиента и импортируйте QR/конфигурацию. Отдельная внешняя авторизация защищает и первоначальный мастер настройки.

Для VLESS:
```bash
sudo python3 tools/manage.py vless-uri
```
Полученный профиль содержит секрет; передавайте его только своему клиенту.

## Обслуживание

```bash
sudo bash menu.sh
sudo bash scripts/backup.sh
sudo bash install.sh --existing
```

Резервная копия включает ключи, .env, runtime/ и data/. Сервисы кратко останавливаются для согласованного снимка и возобновляются после него. Готовые копии можно скачать через панель; команд на хосте она не выполняет.

Восстановление в пустую установку:
```bash
sudo bash restore.sh /secure/location/freenetvpn-TIMESTAMP.tar.gz
sudo bash install.sh --existing
```

Ротация VLESS: sudo bash scripts/rotate_vless.sh --confirm. Она создаёт резервную копию, проверяет новую конфигурацию и при ошибке возвращает прежние настройки. После успеха обновите профили клиентов.

Проверки CI используют настоящие туннели внутри временных Linux Docker-сетей. Они не заменяют подключение к VPS из внешней сети и проверку публичного TLS, UDP, маршрутизации и восстановления. [Чеклист приёмки](docs/acceptance.md), [полная инструкция](README.md), [Spec Kit и незавершённые проверки](specs/001-reliable-core/tasks.md).
