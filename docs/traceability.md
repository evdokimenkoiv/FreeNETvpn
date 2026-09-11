# Требование → реализация → проверка

Эта матрица связывает текущие спецификации с выполняемыми проверками. Этапы 001/002 сохраняют историю решений; расширения этапа 003 имеют приоритет для кабинета и шаблонов.

| Требование | Реализация | Подтверждение |
| --- | --- | --- |
| 001 FR-001/002/004: валидная конфигурация, сохранение ключей | `tools/manage.py`, `tools/protocols.py` | `tests/test_regressions.py`, `tests/test_protocols.py`: повторная конфигурация, PKI, резервная копия, порты |
| 001 FR-003, 003 FR-02: авторизация и CSRF | `admin/app/main.py`, Caddy в `tools/manage.py` | `tests/test_dashboard.py`: вход, cookie, срок сессии, Origin/CSRF, приватные API; `tests/integration.py`: реальный HTTPS |
| 001 FR-005: сохранение SSH и предсказуемый загрузчик | `install.sh`, `scripts/ufw_open_ports.sh` | shellcheck; `tests/bootstrap.sh`: ошибка загрузки/повтор, ref, stdin, отказ перезаписи; внешний SSH-тест остаётся в acceptance |
| 001 FR-006: резервные копии и безопасное восстановление | `tools/manage.py` | unit-тесты архивов/rollback; `tests/integration.py`: создание копии из кабинета, возврат сервисов и скачивание |
| 001 SC-003: WireGuard/VLESS передают трафик | `docker-compose.yml`, конфигурация Xray/wg-easy | `tests/integration.py`: handshake, HTTP через туннель и проверенный TLS |
| 002 FR-201/202: IKEv2 и L2TP/IPsec | `services/ipsec/`, `tools/protocols.py` | `tests/integration_extra.py`: EAP, CHILD_SA, PPP/MSCHAPv2 и HTTP |
| 002 FR-203/204: Outline и AmneziaWG | `services/amnezia/`, `docker-compose.yml`, `tools/protocols.py` | `tests/integration_extra.py`: ключи/handshake/HTTP, перезапуск, отказ отозванному клиенту |
| 003 FR-01/07: удобный кабинет и честные статусы | `admin/app/static/`, `tools/control.py` | `tests/ui.cjs`: Chromium, 1440px/390px, поиск, ошибки сети, экранирование; данные контейнеров проверяются отдельно |
| 003 FR-03/04: разрешённые операции и очередь | `tools/control.py`, `tools/control_agent.py`, `tools/operation_lock.py` | тесты allowlist/idempotency/secret-redaction/сериализации wg-easy; Linux-тест реального systemd/Unix socket |
| 003 FR-05: три VLESS-шаблона | `tools/presets.py`, `tools/protocols.py` | lifecycle/rollback/старый UUID; Linux HTTP через WS, mobile WS и gRPC; QR и отзыв |
| 003 FR-06: три AWG-шаблона без смены ключей | `tools/presets.py`, `tools/protocols.py` | MTU/keep-alive/S/H и ключи в unit-тестах; HTTP всех шаблонов на двух Ubuntu |
| 001 FR-007, 002 FR-206: проверки блокируют плохую сборку | `.github/workflows/ci.yml` | обязательное завершение pytest, bootstrap, lint, browser и двух Linux-матриц |
| Внешняя эксплуатация | [acceptance.md](acceptance.md) | **Не выполнено:** VPS не предоставлен, публичные сертификаты/порты, native apps, reboot/restore не выведены из CI |

Не следует считать наличие `spec.md` или зелёный UI заменой этих проверок. PR должен ссылаться на успешный CI именно для своей текущей версии.
