# Decisions and alternatives

Use root-owned JSON accounts rather than a new writable web database: this keeps the existing deployment and archive boundary. Passwords use PBKDF2-SHA256, session revisions are random to prevent deleted/recreated usernames reviving old cookies. Preserve the original .env administrator as the recovery owner. Additional admins share management powers; owner protection avoids lockout without introducing a third selectable role.

Grant individual profiles rather than whole protocols. Compare credential identity digests so recreating a named VPN client cannot transfer access. Removing a portal account cannot erase keys already imported on devices; explicit VPN revocation remains a separate operation and is clearly described.

Use local paired RU/EN strings and procedural guides. Router guidance must be firmware-specific: expose a general checklist with OpenWrt example, not a universal shell command. Official references (checked 2026-09-14): WireGuard installation, AmneziaWG app guide, Project X clients, Outline downloads, Apple VPN settings, Microsoft VPN settings and strongSwan Android documentation; links are retained in admin/app/static/guides.js.
