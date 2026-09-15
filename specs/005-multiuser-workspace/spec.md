# Feature Specification: Multiuser workspace

**Feature Branch**: `codex/freenetvpn-reliability` (existing delivery branch)
**Created**: 2026-09-14
**Status**: Implementation and validation
**Input**: Improve the dashboard; manage administrators and ordinary users with restricted connection access; provide iOS/macOS/Windows/Android/router instructions, Russian and English UI/documentation, and interface screenshots on GitHub.

## User Scenarios & Testing

### US1 — Manage people and permissions (P1)
Administrators create named accounts, assign an administrator or member role, edit display name/language, reset passwords, disable and delete accounts.
**Why this priority**: The owner must safely delegate management and retain control.
**Independent Test**: Add a second administrator and a member, change permissions and verify old sessions stop working.
**US1/AC1:** Given the existing owner, creating another administrator permits account management; disabling, deleting or resetting an account invalidates its old sessions, while the original owner remains protected.

### US2 — Access only assigned profiles (P1)
Members see and export only their assigned connections and QR codes.
**Why this priority**: Connection keys belong to explicitly authorized users.
**Independent Test**: Two members cannot read each other's profiles or server administration even by requesting their URLs directly.
**US2/AC1:** Given Alice and Bob with different profiles, Alice can export her profile, cannot export Bob's, and cannot access users, jobs, backups, server status or the native WireGuard administration host. Recreated profiles do not inherit assignments merely by reusing a name.

### US3 — Use a clear bilingual workspace (P2)
Administrators use server and people pages; members use a personal connection page. Both can switch Russian/English and follow device instructions.
**Why this priority**: People need to get connected without access to technical administration.
**Independent Test**: Complete login, connection download and device-guide selection in both languages at desktop and phone widths.
**US3/AC1:** Given a member account, the workspace shows only personal connections and instructions for iOS, macOS, Windows, Android and routers; changing language updates the visible interface and survives reload.

### US4 — Discover and deploy from GitHub (P2)
Readers can choose Russian or English documentation and see the actual interface before deployment.
**Why this priority**: Setup and role limitations must be discoverable before adoption.
**Independent Test**: Follow links in both READMEs to installation, roles, guides and reproducible screenshots.
**US4/AC1:** Given the repository, both languages provide the same one-command installation and describe account management, client exports, compatibility limits and labeled demonstration screenshots without private host details or credentials.

### Edge Cases
Duplicate/invalid usernames, unknown roles, unavailable account storage, expired/recreated sessions, self-demotion, protected owner deletion, empty assignments, removed/recreated VPN profiles, failed export, unsupported router firmware, Android without L2TP, language changes while a dialog is open and no horizontal page overflow on phones.

## Requirements

### Functional Requirements
- FR-501: Preserve existing owner credentials and VPN keys during upgrade; include account state in backup/restore.
- FR-502: Administrators can create, edit, disable, delete and reset administrator/member accounts, while the installation owner cannot be deleted or demoted.
- FR-503: Members can read only explicitly assigned profiles and QR codes; all administrative operations and data remain restricted.
- FR-504: Account credential/permission changes invalidate old sessions, including when a deleted username is reused; recreated connection names do not inherit access.
- FR-505: Provide responsive role-specific views with empty, loading and failure states and accessible forms.
- FR-506: Provide Russian and English UI with a persistent language selector and device/protocol-specific instructions for five device families.
- FR-507: Publish linked Russian/English READMEs, account/setup instructions and representative secret-free interface screenshots.
- FR-508: Distinguish portal account removal from revocation of already downloaded VPN credentials in management flows and documentation.

### Key Entities
Account (username, display name, role, enabled state, language), connection assignment (profile identity and account), session (account revision and expiry), device guide (platform/protocol/language), and account audit event without secrets.

## Success Criteria
- SC-501: All declared member-to-admin and member-to-other-profile denial cases pass, including direct downloads, QR and Basic authentication.
- SC-502: Account creation/assignment/edit/delete and member profile/guide journeys pass in browser at 1440px and 390px without horizontal page overflow or script errors.
- SC-503: Both READMEs link the same installation procedure and five device families; screenshot reproduction and account-state backup roundtrip pass validation.

## Assumptions
One server, no billing or public signup. Admins have equivalent management powers except the protected installation owner. Administrators assign existing per-device profiles, may assign a profile to multiple accounts and communicate initial passwords privately. Account deletion/disable blocks portal access; already issued VPN keys require explicit profile revocation. Browser language selection overrides an account's default language. Guides describe supported clients and firmware-dependent limitations, not universal connectivity guarantees.
