# Implementation plan

> Исторический этап разработки. Актуальное расширение: [003 — кабинет и шаблоны](../003-dashboard-presets/spec.md). Ограничение «read-only panel» заменено разрешёнными операциями через локальный агент; требования сохранности данных и запрет общего command API действуют. Все шесть протоколов восстановлены в [этапе 002](../002-all-protocols/spec.md).

## Architecture

Caddy terminates HTTPS and preserves /admin and VLESS WebSocket paths. FastAPI supplies read-only administration and a forward-auth endpoint for the separate wg-easy hostname. Password verification uses PBKDF2-SHA256. No Docker socket is mounted in the panel.

wg-easy 15.4.0 owns WireGuard peers/database. Its native setup wizard is protected by Caddy forward-auth; the operator chooses the endpoint/UDP port from .env. Xray 26.3.27 receives rendered JSON. Runtime data uses bind mounts under data/ so one consistent backup covers it. Container code/configuration is read-only where feasible.

The Python standard-library management tool owns validated configuration and archive operations. Shell entry points own Ubuntu/Docker/UFW setup. No shell sources .env. Legacy configuration triggers a migration error rather than replacement.

## Constitution check

Preserves data, removes host-command web capabilities, protects admin surfaces, validates generated config, adds failing CI, distinguishes local and external VPN tests. Production deployment and external network acceptance remain separate from code verification.

## Validation

Unit/API regression tests; ShellCheck and bash -n; real Linux Docker integration on Ubuntu 22.04 and 24.04. Integration uses a Caddy internal CA trusted explicitly by test clients, real Xray server/client, and a kernel WireGuard peer. External acceptance follows docs/acceptance.md.

## Sources

- https://wg-easy.github.io/wg-easy/latest/advanced/config/optional-config/
- https://wg-easy.github.io/wg-easy/latest/advanced/config/unattended-setup/
- https://wg-easy.github.io/wg-easy/latest/examples/tutorials/caddy/
- https://github.com/wg-easy/wg-easy/releases/tag/v15.4.0
- https://github.com/XTLS/Xray-core/releases/tag/v26.3.27
- https://github.com/caddyserver/caddy/releases/tag/v2.11.4

## Technical context and project structure

Python 3.12 for development/CI; stdlib management and Spec Kit helper scripts; FastAPI admin with pinned dependencies; Docker Compose and systemd on Ubuntu 22.04/24.04 x86_64 for runtime. Windows supports development checks, not the VPN server runtime. Sources live in tools/, admin/, services/ and scripts/; tests/ contains regression, browser and Linux traffic suites. No runtime dependency on Specify CLI.

## Design artifacts

- research.md records decisions and rejected alternatives.
- data-model.md defines ownership, secret boundaries and invariants.
- contracts/ defines this feature's external interface; 003 owns the cabinet/agent contract.
- quickstart.md gives the repeatable validation path.

## Phases and constitution check

Setup establishes artifact/dependency inputs; foundation validates ownership/security; each prioritized story is implemented and independently verified; final cross-cutting checks preserve historical evidence and external acceptance. tasks.md lists exact source/test paths and dependencies. All six constitution principles apply: reproducible checks; preserve existing secrets/data; authenticated administration without arbitrary commands; validate configuration as data; failing CI; secret-free Git and explicit external limitations. No exception is requested.
