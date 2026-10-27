# Installation errors: fix and resume

[Русский](installation-errors.ru.md)

The installer reports an error code, observed cause, verification steps and a retry command. Select English with `sudo env FREENET_LANG=en bash install.sh` (add `--existing` when `.env` is already saved), or Russian with `FREENET_LANG=ru`. Otherwise `LANG` selects the language.

## Identical hostnames are an input error, not a DNS error

Entering `magic.llnit.com` twice produces `CONFIG_HOSTS_EQUAL`: the VPN portal and WireGuard UI require distinct hostnames. DNS has not been checked yet. The updated installer retries the offending hostname before asking for a password.

| Field | Example | DNS |
|---|---|---|
| DOMAIN — VPN portal | `magic.llnit.com` | A → this machine's public IPv4 |
| WG_DOMAIN — WireGuard UI | `wg.magic.llnit.com` | A → the same IPv4 |

Create the records at your DNS provider. Record names depend on the edited zone: in `llnit.com`, they are typically `magic` and `wg.magic`. Use the public IP of the VPS being installed. Do not enter `https://`, a port or a path.

In older versions, `WireGuard UI needs its own hostname (WG_DOMAIN)` aborts after password entry but before saving a new `.env`. Correct the second hostname and rerun without `--existing`. Waiting for DNS alone cannot fix identical values.

## DNS, HTTPS and services

| Code | Observed condition | Fix and verification |
|---|---|---|
| `CONFIG_DOMAIN` | Invalid hostname syntax | Use a name such as `vpn.example.com`, without scheme/port/path. |
| `DNS_NO_IPV4` | Server resolver returned no IPv4 | Check A record, hostname, zone delegation and resolver. Recent changes may be cached. Repeat `getent ahostsv4 HOSTNAME`. |
| `DNS_LOOKUP_FAILED` | Resolver check failed/timed out | Check server networking and DNS. This does not prove the provider has no record. |
| `HTTPS_DNS` | curl could not resolve the hostname | Repeat the DNS check; the corrected answer should match the VPS IP. |
| `HTTPS_CONNECT` / `HTTPS_TIMEOUT` | Connection/response unavailable within the limit | Compare the IP; check Caddy and inbound TCP 80/443 at the provider and host. Also test from another network: NAT loopback can affect the server probe. |
| `HTTPS_TLS` | TLS/certificate verification failed | Check A/AAAA, ports 80/443, server time and Caddy issuance errors. Fix the reported cause and allow issuance to finish; do not disable TLS checks. |
| `HTTPS_BACKEND` | HTTPS returned 502/503/504 | Check admin/Caddy and, for the WireGuard host, wg-easy. DNS propagation alone is not an adequate diagnosis. |
| `HTTPS_AUTH` | Anonymous request did not receive the expected 401 | Check the destination IP, Caddy routing/forward_auth and admin health. Access protection is not confirmed yet. |
| `HTTPS_RESPONSE` | Unexpected status or health body | Confirm the domain reaches this installation: another website can return 200. Check routing and admin health. |
| `SERVICE_STOPPED` / `INSTALL_STAGE` | A service stopped or the named stage failed | Follow the stage guidance and original error above. For occupied ports, use `sudo ss -lntup` and identify the owner before stopping services. |
| `INSTALL_DOWNLOAD` | Project/dependency download failed | Check APT/curl/tar errors, GitHub access, disk space and the selected version. Fix and repeat the original command. |
| `CONFIG_READ` | No valid saved configuration | If `.env` exists, run `sudo python3 tools/manage.py validate` and correct the named field. If absent, repeat normal setup. |

DNS checks run **before Docker installation and image downloads**, after settings are saved. Compare displayed addresses with the VPS panel. The check observes this server's resolver; it does not prove worldwide propagation, open inbound ports or correctness of every AAAA response. Correct unusable AAAA records, or remove them when the service does not use IPv6.

## After fixing the cause

Use the installation directory (normally `/opt/freenetvpn`, or your custom `INSTALL_DIR`). When `.env` **does not exist**, repeat setup:

```bash
cd /opt/freenetvpn
sudo env FREENET_LANG=en bash install.sh
```

When `.env` **exists**, correct only the named fields with `sudo nano .env` if necessary. Validate and reapply saved settings:

```bash
cd /opt/freenetvpn
sudo python3 tools/manage.py validate
sudo env FREENET_LANG=en python3 tools/diagnostics.py dns
sudo env FREENET_LANG=en bash install.sh --existing
```

Keep `--no-firewall` on retries if originally selected. Preserve `.env`, `data/`, keys, users and backups. `--existing` repeats installation stages and recreates containers, potentially interrupting active connections briefly. For verification alone, use `sudo bash scripts/health_check.sh`.

Inspect locally:

```bash
sudo python3 tools/manage.py compose ps
sudo python3 tools/manage.py compose logs --tail 60 caddy admin
```

Add `wg-easy` for the WireGuard UI. Do not publish full logs containing private data. The installer does not print failed command arguments or bypass TLS; review third-party APT/Docker/service output before sharing it.

`--existing` **does not download new code**. Obtain updated diagnostics using the [deployment guide](deployment.md), preserving state. Rerunning the downloaded entry point also reuses the existing directory. Successful server checks do not replace client-device connection and traffic verification.

[Image download/disk errors and one-command updates](update.en.md).
