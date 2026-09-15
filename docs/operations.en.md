# Traffic and maintenance

[Русский](operations.ru.md) · [English](operations.en.md)

Administrators have **Traffic** and **Maintenance** pages. Members cannot query these APIs. A 30-second background sampler retains up to 24 hours of aggregate rate history across agent restarts; current service totals reset when containers restart. A dash means unavailable, never zero. Rates need two samples and gaps/resets interrupt the chart. The data is private and included in backups.

| Measurement | Meaning |
| --- | --- |
| RX / TX | Bytes on service bridge interfaces since container start; includes overhead and both proxy legs, not user billing |
| WireGuard / AmneziaWG | Peers with a handshake in the past 180 seconds; not guaranteed internet reachability |
| VLESS / Outline / MTProto / HTTP-SOCKS | Established inbound TCP sockets on configured service ports; not distinct people or authenticated sessions. Outline UDP sessions are unavailable |
| IKEv2 / L2TP | Established IKE SAs separately; shared IPsec byte totals counted once |

The 24-hour chart is aggregate service rate, not historical per-user accounting. No peer key, IP address or browsing history is collected. Temporary telemetry failures never stop VPN services.

Maintenance reports disk usage, journal/Docker usage, and whether the OS requests a reboot. **Check now** compares the recorded source commit with the `main` GitHub branch and simulates APT upgrade using the existing local package index. It shows the oldest index timestamp; missing network data is unavailable, not up-to-date. It never updates package indexes, installs software, pulls images or restarts services. Container-image update discovery is not part of this check. Review changes and make an off-server backup before upgrading.

Cleanup always requires a preview and confirmation valid for five minutes. Only two fixed actions exist:

- **Archived journals:** `journalctl --vacuum-time=7d`, archived system journals older than seven days across the entire host. Active journal files remain; no forced rotation.
- **Docker build cache:** `docker builder prune --force --filter until=168h`, dangling build cache older than seven days across the entire host, including other projects. No `--all`, image/container/volume/system prune. Future builds may take longer.

The preview shows current usage, not a promise of exact reclaimable bytes. The job records free space before/after; concurrent writes can make the delta negative. Confirmation tokens are single-use even on failure; preview again to retry. Jobs interrupted by an agent restart are marked interrupted and must be inspected before retrying. Application profiles, keys, accounts, backups, images and containers are preserved. Docker logs rotate at 10 MB × 3 files per container on creation/recreation; existing logs are never manually truncated. Keep off-server backups; see [recovery](recovery.en.md).
