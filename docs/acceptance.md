# External acceptance before production use

Use a disposable Ubuntu 22.04/24.04 server and a client on a different network. Record OS, commit, image versions and results without publishing secrets.

1. Point DOMAIN and WG_DOMAIN directly to the public IPv4. Remove unusable AAAA records; permit inbound 80/443 TCP and the configured WireGuard UDP port in the provider firewall. Do not use an HTTP-only CDN proxy for the WireGuard endpoint.
2. Install using README instructions. Verify the installer fails explicitly for missing DNS/blocked HTTPS; valid setup must pass health_check.sh. Confirm a second SSH session can still connect on the original port and authentication method.
3. Confirm trusted public TLS, 401 for /admin and the WireGuard hostname without credentials, and successful authenticated UI. Do not disable certificate verification.
4. Complete the wg-easy wizard with endpoint=DOMAIN and port=WG_PORT. Create a client, import its QR/config, connect from the external network. Verify a new handshake, HTTP/HTTPS egress and DNS resolution through the tunnel. Repeat after server reboot. Changing endpoint/port later requires updating both wg-easy and .env.
5. Export VLESS with tools/manage.py vless-uri. Import it into a compatible client, verify TLS hostname/certificate, WebSocket path and internet egress. Test a wrong UUID: the tunnel must fail. Confirm traffic works after reboot.
6. Repeat install.sh --existing; compare UUID, admin login and WireGuard clients. They must remain unchanged.
7. Create a backup with scripts/backup.sh. Services should resume automatically. Move the archive securely to a fresh v2 checkout/server, restore.sh, review DNS and install.sh --existing. Existing clients should retain their identities. Do not restore over existing data.
8. Rotate VLESS explicitly using scripts/rotate_vless.sh --confirm, export the new profile, verify old credentials fail and new credentials succeed. Preserve the automatic pre-rotation backup.

CI verifies real encrypted transport inside temporary Linux Docker networks using a private test CA. It does not prove public UDP reachability, provider firewall behavior, public CA issuance, regional availability or a full root installer run on the target VPS.
