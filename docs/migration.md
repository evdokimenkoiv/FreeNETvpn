# Version 2 and legacy installations

Version 2 supports WireGuard, VLESS, IKEv2, L2TP/IPsec, Outline and AmneziaWG. Original incomplete helpers are retained under legacy/ for reference; active IKEv2/L2TP entry points use the managed CLI. Existing v2 installations keep their enabled protocols. After updating code, use `sudo python3 tools/manage.py services all` (creates a backup), then `sudo bash install.sh --existing` to enable all services. See [protocol operations](protocols.md).

Do not overwrite a working legacy server. The new configure command rejects .env files without CONFIG_VERSION=2. Existing Docker named volumes are not deleted or automatically converted.

For migration, first export wg-easy clients and back up the old .env, services/, host/, Docker named volumes and any host IPsec/PPP secrets using the old server's tooling. Deploy v2 in a separate directory or disposable server and validate it before retiring the old stack. wg-easy v14-to-v15 requires the upstream migration procedure; never copy old JSON over a live v15 database. The v2 restore command accepts only backups produced by v2, not the old incomplete services/host-only archives.

WireGuard UI now uses WG_DOMAIN (a separate DNS name), replacing the unreliable /wg subpath. First login is HTTP Basic authentication using the generated FreeNETvpn account; then complete wg-easy's native account/endpoint wizard. Set endpoint=DOMAIN and the UDP port from WG_PORT. Afterwards create/import clients. Native wg-easy account recovery follows upstream instructions; it is distinct from the outer FreeNETvpn account.

IPv4 is the validated baseline. Automatic IPv6/SSH hardening/SSH 2FA from the old installer are not enabled. No SSH settings are changed. Public TLS remains enabled; firewall rules preserve detected SSH listener ports.

Upstream migration guide: https://wg-easy.github.io/wg-easy/latest/advanced/migrate/from-14-to-15/
