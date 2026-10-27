# Feature Specification: Stateful one-command updates

## User Scenarios & Testing
### US1 — Update without losing users (P1)
An operator updates an existing archive or Git installation using one command, keeping settings, identities and keys.
**US1/AC1:** A validated pinned release is applied only after a consistent backup; a failed application can resume its saved revision without replacing current user state.
### US2 — Diagnose and recover (P1)
An operator understands a failed image pull and can explicitly roll back a saved update.
**US2/AC1:** Disk/inode exhaustion is distinguished from DNS, registry authorization, missing images, rate limits and TLS; rollback requires explicit state restoration and retains newer state for recovery.

## Requirements
- FR-901: Resolve and download an exact commit; reject archive traversal, links and protected state paths before applying code.
- FR-902: Stop writers for a consistent snapshot of configuration, accounts and VPN state, preserve old code, and serialize updates with a lock.
- FR-903: Preserve .env/data/backups during updates, regenerate runtime from saved configuration, and publish deployed revision only after installer checks pass.
- FR-904: Retain a pending transaction across failures and resume the pinned candidate without overwriting current users with an older snapshot.
- FR-905: Require explicit --restore-state for rollback; retain a rescue copy of newer state and document limitations.
- FR-906: Classify Docker pull failures and check storage/inodes before image downloads; never infer website DNS failure from a generic exit code.
- FR-907: Provide equivalent RU/EN one-command instructions for old archive installations, recovery and disk errors.
- SC-901: Fault-injection tests prove state preservation, backup-before-apply, retry and rollback boundaries; shell fixtures execute the documented command.

## Boundaries
Updates have a maintenance window. They do not modify firewall rules, reset secrets or merge user databases across snapshots. Rollback does not revert OS packages or guarantee offline image availability. Existing client/device acceptance gates remain. No production installation is modified to validate this feature.
