# External acceptance before production use

Use a disposable Ubuntu 22.04/24.04/26.04 server and a client on a different network. Record OS, commit, image versions and results without publishing secrets.

1. Point DOMAIN and WG_DOMAIN directly to the public IPv4. Remove unusable AAAA records; permit inbound 80/443 TCP and every selected [VPN port](protocols.md) in the provider firewall. Do not use an HTTP-only CDN proxy for UDP VPN endpoints.
2. Install using README instructions. Verify the installer fails explicitly for missing DNS/blocked HTTPS; valid setup must pass health_check.sh. Confirm a second SSH session can still connect on the original port and authentication method.
3. Confirm trusted public TLS, 401 for /admin and the WireGuard hostname without credentials, and successful authenticated UI. Do not disable certificate verification.
4. Complete the wg-easy wizard with endpoint=DOMAIN and port=WG_PORT. Create a client, import its QR/config, connect from the external network. Verify a new handshake, HTTP/HTTPS egress and DNS resolution through the tunnel. Repeat after server reboot. Changing endpoint/port later requires updating both wg-easy and .env.
5. Export VLESS with tools/manage.py vless-uri. Import it into a compatible client, verify TLS hostname/certificate, WebSocket path and internet egress. Test a wrong UUID: the tunnel must fail. Confirm traffic works after reboot.
6. Repeat install.sh --existing; compare UUID, admin login and WireGuard clients. They must remain unchanged.
7. Create a backup with scripts/backup.sh. Services should resume automatically. Move the archive securely to a fresh v2 checkout/server, restore.sh, review DNS and install.sh --existing. Existing clients should retain their identities. Do not restore over existing data.
8. Rotate VLESS explicitly using scripts/rotate_vless.sh --confirm, export the new profile, verify old credentials fail and new credentials succeed. Preserve the automatic pre-rotation backup.

9. For IKEv2, create/export a named EAP client, trust the exported CA, verify the server remote ID, then connect from a different network and check internet/DNS. For L2TP/IPsec, use the PSK and named PPP account; ensure no plaintext L2TP service is reachable. Test wrong passwords and two clients behind a NAT using the actual target operating systems.
10. Import an Outline access key and an AmneziaWG configuration. Verify TCP/UDP applications, internet/DNS and protocol-specific handshakes where available. Revoke each test account/key and confirm that reconnecting fails. Test Outline API remains unreachable from the public network.
11. Repeat the new-protocol connections after reboot and after restoring the complete backup to an empty installation. Confirm CA, server keys, Outline keys and AmneziaWG parameters remain unchanged. Apple mobileconfig and native Windows/mobile imports require their own platform acceptance.

12. Sign in to the [cabinet](dashboard.md) on desktop and mobile. Connect its native wg-easy account; create/export/revoke clients of all selected protocols. Try all VLESS/AWG presets in the actual client apps, including gRPC support and importing mobile VLESS as Xray JSON. Check old keys still work after a template change and that the refreshed configuration has the selected settings.
13. Create a backup from the cabinet. Re-enter the session after services return if necessary, verify the operation finished and download the archive. Test expired sessions, forbidden cross-origin changes and an unavailable local agent. No dashboard response or job history should disclose backend tokens/passwords unless it is an explicit client export.

CI verifies encrypted transport inside temporary Linux Docker networks using test certificates. It does not prove public UDP reachability, provider firewall behavior, public CA issuance, regional availability, native client UI imports or a full root installer run on the target VPS.

Recorded Ubuntu 26.04 VPS results: [qualification report](vps-qualification.md). Partial evidence does not close the full external gate.

14. For optional HTTP CONNECT/SOCKS5, test external HTTPS egress with correct credentials, denial without credentials and after revocation, and denial of loopback/private/link-local destinations. SOCKS5 UDP is intentionally disabled. Verify the app uses proxy-side DNS when needed.
15. For MTProto, import the assigned padded-secret link into native Telegram on each target device and verify message/media loading on the intended network. An anonymous `req_pq_multi`/`resPQ` nonce roundtrip tests Telegram transport, not account sign-in, app UX, calls or regional availability. Feature 006 SC-602 stays open until that native-device evidence is recorded.
16. Follow [recovery](recovery.en.md), including account/assignment inventory and post-restore revocations. A successful empty-directory extraction alone does not complete the full recovery drill.
