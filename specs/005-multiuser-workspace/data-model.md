# Data model

data/control/accounts.json: version=1, users keyed by case-sensitive ASCII username, bounded audit list. User: display_name, role=admin|user, enabled boolean, locale=ru|en, password_hash, random revision, grants[{protocol,name,identity}], is_owner=false. Owner is synthesized from validated .env and cannot be edited here. At most 1000 added accounts, 500 assignments/account and 200 audit entries.

An audit record contains actor, action, target and timestamp only. Hashes and audit metadata never contain passwords. Sessions remain process-local for eight hours, contain username/revision/CSRF, and are lost on web restart. Permission, credential and enabled-state changes invalidate prior revisions. No email address, phone or external identity provider is required.

Assignments use a digest of the protocol client identity (UUID/public key/credential or native key ID). Member snapshots omit identity, jobs, server metrics, backup metadata, native administration hostname and other accounts. Export is checked again against the current snapshot by the agent before returning keys.
