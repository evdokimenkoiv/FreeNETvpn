# One-command updates

[Русский](update.ru.md)

For an existing `/opt/freenetvpn` installation, including older versions without `update.sh`:

```bash
sudo bash -c 'set -e; f=$(mktemp); trap "rm -f -- \"$f\"" EXIT; curl -fsSL --retry 3 https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/main/update.sh -o "$f"; bash "$f"'
```

Once installed, use `sudo bash /opt/freenetvpn/update.sh`; it also obtains the current updater. For a custom location, pass `INSTALL_DIR=/your/directory` using `sudo env` before `bash`. `FREENET_REF=REVIEWED_SHA` selects a pinned version; the default is `main`. Choose a revision with passing CI. The dashboard's update check remains read-only and does not install anything.

Requirements: an existing valid `.env`, Python 3, curl, Docker and Ubuntu/systemd. The updater does not create replacement passwords, keys or accounts. Fix failed image downloads before retrying an incomplete installation. Free disk space first if storage is full; updates need room for backups too.

## Update sequence

1. Resolve an exact commit and download that archive. Validate archive paths, a private copy of configuration, available space and local managed-code changes. Failures before stopping services leave them running.
2. Stop services and the local control agent. VPN connections are interrupted during backup, image download/build and checks; schedule a maintenance window and finish dashboard operations first.
3. Save a private `.updates/ID/state.tar.gz` containing `.env`, `data` and `runtime`, previous replaced code in `old-code/`, and a standalone `updater.py`. State includes accounts, roles, assignments, VPN keys and WireGuard state. The directory is root-only and unavailable through the dashboard. Copy it to separate storage privately.
4. Replace project files, preserving `.env`, `data`, `runtime`, `backups` and `.git` from archive overwrite. The installer regenerates runtime files from saved settings. Remove only obsolete files listed by the previous update manifest, after saving their old content.
5. Run `install.sh --existing --no-firewall`, including HTTPS, authentication and protocol checks. Firewall rules remain operator-managed. On success, write the deployed commit to `data/release.json` for the maintenance page.

Concurrent updates are locked out. Snapshots are not automatically deleted. State-space preflight reserves twice its uncompressed size plus a margin; it does not estimate all Docker images. The installer also checks free space/inodes on the installation, Docker and standard `/var/lib/containerd` filesystems before image download. Check custom containerd storage separately.

For Git installations, the first update refuses modified tracked files. Subsequent updates use a hash manifest without changing Git history; `git status` may show updater-applied changes. Do not mix this workflow with server-side `git pull`/`reset`. Save and reconcile local managed-code edits separately; configuration and user-data changes do not fail the code check. For old archive installations, the updater cannot distinguish initial local code edits from the original release, so it saves all replaced files in `old-code`.

## Interrupted updates

Fix the reported cause and repeat the same command. A pending transaction resumes **the same saved commit**, without resetting accounts or state. Run again after completion to obtain any newer revision.

If GitHub is unavailable after application started, continue locally:

```bash
sudo python3 /opt/freenetvpn/.updates/updater.py --root /opt/freenetvpn
```

Package/image downloads may still require networking. A failure after stopping can leave services stopped. Preserve `.updates/pending.json`, `.env` and `data`. The updater does not automatically revert user state after failure, because users may have been added after the candidate started.

## Explicit rollback

Find the ID in the printed backup path or `sudo ls -1 /opt/freenetvpn/.updates`, and replace `ID`:

```bash
sudo python3 /opt/freenetvpn/.updates/ID/updater.py --root /opt/freenetvpn --rollback ID --restore-state
```

`--restore-state` explicitly restores **both code and users/settings at snapshot time**. Later changes cease to be active. Before rollback, current state is archived to `ID/rescue-.../state.tar.gz`; original directories are moved there without deletion. They can be restored into a clean installation separately. Users from different snapshots are not automatically merged.

Rollback reapplies the old installer and checks services. It does not revert OS packages, firewall or kernel, and may still need image-registry access. State archives omit the reproducible `caddy_config` Docker volume; Caddy certificates in `data/caddy` are included. For another-machine recovery, see the [recovery guide](recovery.en.md). Verify a real external client connection after updating or rolling back.

## Image downloads: `no space left on device`

Docker/containerd lacks free blocks, inodes or quota; the VPN website's DNS propagation is unrelated:

```bash
df -h / /var/lib/containerd
df -i / /var/lib/containerd
sudo docker system df
sudo apt-get clean
```

Recheck free space. Enlarge the VPS disk or deliberately remove unneeded cache if necessary. Do not manually delete `/var/lib/containerd`, use `docker system prune --volumes`, or delete VPN state/the last backup to make room. Once fixed, resume installation from `/opt/freenetvpn` with `sudo bash install.sh --existing`, or resume a pending update with the update command above.

`--env-file /opt/frenv` differs from the normal `/opt/freenetvpn/.env`. If present in the actual output, inspect the installed `tools/manage.py` version and the existence of `.env` without printing secrets. When Docker has already started downloading and reports no space, that storage error is the established failure cause.
