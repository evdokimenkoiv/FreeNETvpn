# Ubuntu 26.04 VPS qualification

Date: 2026-09-11. This report records an operator-authorized deployment on a fresh public x86_64 KVM VPS. Hostnames, IP, credentials, profiles and backup archives are handed to the owner privately; they are not repository fixtures.

Source: `eb45c0c81e8f5af127940b81a963b4035c5ac94d`, with only the installer OS allowlist/help extended to Ubuntu 26.04 before deployment. That extension and this evidence are committed together. The original installer explicitly rejected the unsupported release before mutating the host. No protocol implementation was changed to obtain these results.

Environment: Ubuntu 26.04 LTS, Linux 7.0.0-14-generic, Python 3.14.4, 1 vCPU, approximately 1.6 GiB RAM, 40 GB disk. Docker Engine 29.8.0 and Compose plugin 5.5.1 were installed from the official Docker Ubuntu repository. CI remains Ubuntu 22.04/24.04; this host qualification does not imply a 26.04 CI matrix.

| Check | Observed result | Boundary |
| --- | --- | --- |
| Full root installation | `bash install.sh --existing` exited 0; all six protocols started, seven containers running; root control agent active | Pinned source was downloaded and configured before invoking the installer. The one-command bootstrap itself is tested separately in CI. |
| Public DNS and TLS | Both administration hostnames resolved to the VPS; publicly trusted certificates issued; external HTTPS validation passed | No disabled TLS verification or internal test CA |
| Authentication and browser | Anonymous cabinet and WireGuard host returned 401; authenticated desktop/mobile Chromium passed with no JavaScript errors or horizontal overflow | Native wg-easy setup and cabinet account connection completed |
| SSH and firewall | Original password-based SSH still worked in a second connection and after reboot; UFW active with the selected VPN/HTTPS ports | SSH settings were preserved; no claim that every public UDP protocol was exercised |
| Clients | Named client creation and private export passed for all six protocols | Export success alone is not a native-client traffic test |
| VLESS | All three presets (WebSocket/TLS, mobile WebSocket, gRPC/TLS) carried an HTTPS internet probe from an external Windows Xray client with the VPS egress IP; revoking each test client rejected reconnects | Post-reboot repeat also passed for the persistent WebSocket client |
| Outline | External Windows Xray Shadowsocks client carried HTTPS with the VPS egress IP; revoked access key rejected reconnects; persistent client passed again after reboot | Native Outline application and UDP applications remain untested on this VPS; management listener was confirmed bound to loopback |
| WireGuard | External Windows userspace probe established a public UDP handshake. A separate Linux kernel WireGuard client carried HTTPS internet egress and DNS through the tunnel | The Linux client ran in an isolated container on the same VPS, connecting to the server container's internal address. The external Windows probe completed TLS but timed out reading HTTPS headers. This does **not** close external WireGuard acceptance; the cause remains unresolved. |
| IKEv2, L2TP/IPsec, AmneziaWG | Daemons started and persistent client exports succeeded | Native external application, provider/NAT and preset traffic acceptance remains open; earlier Linux packet CI is a separate result |
| Cabinet backup | Asynchronous backup completed; services restarted and the authenticated archive download succeeded | Archive contains secrets and was handed to the owner privately |
| Restore | Archive restored into a new empty directory; all 43 configuration/data files were byte-identical to the archive; runtime rendering and configuration validation succeeded | Restored copy was not started as a second deployment. Full restore with live client reconnection on a clean installation remains open. |
| Repeated installation | A second `install.sh --existing` exited 0; admin configuration and five directly compared protocol exports remained identical | IKE credentials and CA were also compared across the backup/reboot boundary |
| Reboot | Actual boot ID changed; public HTTPS returned approximately 26 seconds after initiating reboot; all seven containers and root agent started without intervention; no failed systemd units | All six client identities survived: five exports unchanged, IKE credential JSON and CA unchanged. Apple profile wrapper UUIDs are generated on export and are not persistent VPN identities. External VLESS and Outline traffic passed again. |

Temporary acceptance clients were revoked. Persistent owner profiles were retained. No secrets were included in source commits or CI output.

The three existing external tasks remain open. Before full production sign-off, finish external WireGuard HTTPS/DNS in the target native application, native IKEv2/L2TP/AmneziaWG and all relevant preset/NAT/UDP cases, and a clean restored deployment with live reconnects. Explicit VLESS rotation acceptance is also outstanding; test-client revocation is not represented as full rotation. See [the complete procedure](acceptance.md).
