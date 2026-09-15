# Restore a backup

[English](recovery.en.md) · [Русский](recovery.ru.md)

The administrator creates and downloads backups from **Backups**. Creation briefly stops the Compose services for a consistent snapshot and restarts them even if archiving fails. Copy the archive off the VPS. It contains secrets: `.env`, generated runtime configuration and `data/`, including VPN/proxy identities, account password hashes and profile assignments. Source code is not included; record the deployed Git commit alongside the archive.

## Recovery procedure
1. Prepare a replacement Linux machine using the same source revision and supported Docker/Compose prerequisites. Copy the archive there privately. Stop the old instance before using the same identities on the replacement.
2. In that source checkout, ensure `.env`, `runtime/` and `data/` are absent/empty. Restore refuses an occupied destination. Never delete production state to work around that refusal. Make a separate fresh checkout for a rehearsal.
3. Run from that checkout:
   ```bash
   sudo bash restore.sh /absolute/path/freenetvpn-backup.tar.gz
   sudo python3 tools/manage.py validate
   ```
4. Point the original main and WireGuard hostnames to the replacement server. Retaining the same names and ports preserves exported client endpoints. If changing them, plan profile reissue and certificate migration separately.
5. Start the recovered installation:
   ```bash
   sudo bash install.sh --existing
   sudo bash scripts/health_check.sh
   ```
6. Sign in with the restored owner, verify people/assignments and test a member account. Check HTTPS certificates, actual client traffic and DNS, and confirm revoked credentials remain rejected. Compare the recovered configuration/key inventory with the archive before declaring recovery complete.

## Boundaries
Restore validates archive paths/types and refuses traversal, links and an occupied destination before extraction. A backup archive is confidential input from a trusted administrator; it is not encrypted or independently signed by this feature. It does not back up arbitrary host files, SSH configuration, firewall policies outside this installer or external DNS. Restoring old state also restores old passwords and may resurrect credentials revoked after that backup; audit and revoke them again.

Empty-directory extraction and identity comparison alone are not a complete disaster-recovery exercise. A full drill requires starting the restored deployment and reconnecting external clients. The browser offers instructions and downloads, never an overwrite-live-server restore button.
