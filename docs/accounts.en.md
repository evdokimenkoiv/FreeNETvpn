# People and access

**English** · [Русский](accounts.ru.md) · [Home](../README.md)

| Capability | Administrator | Member |
| --- | --- | --- |
| Manage services, profiles, accounts and backups | Yes | No |
| Download profiles and QR codes | All profiles | Explicitly assigned profiles only |
| Native wg-easy administration | Yes, with native credentials | No |
| Setup guides and RU/EN language | Yes | Yes |
| Change own portal password | Additional accounts; owner via server configuration | Yes, with current password |

The installation owner is the original .env administrator. Its username/password and all VPN keys survive upgrade; it cannot be deleted, disabled or demoted from the portal. Added administrators have full server/account/profile control. Do not give that role to someone who should only connect a device.

## Add a person

1. Create a separate VPN profile for their device in **Connections**.
2. Open **People → Add person**. Enter a display name and a unique username (1–64 letters, digits, dash or underscore).
3. Choose **Member** for personal downloads, or **Administrator** for full management. Set a default language and a password of at least 16 characters.
4. Select the profiles for a member. Administrators can access all profiles automatically. A new member with no assignments sees an explanatory empty state.
5. Save and share the initial credentials privately. Users sign in at the same /admin address; their workspace is selected by their role. Each can change their password from the account button.

## Edit, reset or remove

Open **Manage access** on an account card. Change role, profile assignments, default language, display name or sign-in permission. Enter a new password to reset it; leave the field empty to retain it. Saving changes invalidates old sessions immediately. Self-deletion/self-demotion and owner modification are rejected. The account audit records who changed which account, without passwords.

**Portal access and VPN access are different.** Disabling/deleting an account or unassigning a profile cannot erase a key already imported on a device. To disconnect VPN access, revoke that profile in Connections. Revocation may restart its service and briefly affect other connections. A profile assigned to several people stops working for all of them when revoked. Prefer a profile per device.

Assignments track client identity, not just a reusable name. Recreated profiles require a new explicit assignment. Existing sessions also cannot survive deleting/recreating a username. Expired, disabled and changed accounts must sign in again. Browser language preference is saved locally and takes precedence over the account default.

## Upgrade and recovery

Create/download a backup first. For a Git checkout, fetch and fast-forward your reviewed branch; for an archive installation download the reviewed source archive into a temporary directory, verify it excludes .env/data/runtime/backups, then copy only source files into /opt/freenetvpn. Do not delete persistent directories. Run `sudo bash install.sh --existing`: it restarts the root agent and rebuilds/recreates the web service. It does not download code itself. A web restart ends sessions, so sign in again with the same owner credentials.

Additional accounts, assignment identities and audit history are stored privately at data/control/accounts.json and included in standard backups. Restore only into a clean checkout of this version with no existing .env/runtime/data: `sudo bash restore.sh /path/to/backup.tar.gz`, then review DNS and run `sudo bash install.sh --existing`. Test reconnection before retiring an old server. Backups and exported profiles contain secrets; do not commit or publish them.

The web container stays read-only/non-root. The root Unix agent owns writes, validates fixed methods and serializes account/profile/backup operations. Both session and Basic authentication enforce the same roles. Members cannot download server backups or enumerate other users. Public static device guides contain no credentials.
