# Implementation plan

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
