#!/usr/bin/env bash
# Works both from a downloaded temporary file and an installed checkout.
set -Eeuo pipefail
umask 077
[[ ${EUID} -eq 0 ]] || { echo 'Run with sudo bash update.sh'; exit 1; }
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="${INSTALL_DIR:-/opt/freenetvpn}"
[[ ! -f "$source_dir/tools/manage.py" ]] || root="$source_dir"
[[ -f "$root/.env" && -f "$root/tools/manage.py" ]] || { echo 'Existing installation and .env required; check INSTALL_DIR.'; exit 1; }
stage="$(mktemp -d)"
trap 'rm -rf -- "$stage"' EXIT
trap 'echo "ERROR [UPDATE_DOWNLOAD]: check curl/Python errors above and GitHub connectivity. Active code/settings were not changed. Retry this command, or run the installed tools/update.py directly." >&2' ERR
ref="${FREENET_REF:-main}"
[[ "$ref" =~ ^[a-zA-Z0-9._-]+$ ]] || { echo 'FREENET_REF must be a branch/tag name without slashes or a commit SHA'; exit 1; }
curl -fsSL --retry 3 --connect-timeout 15 --max-time 120 "https://api.github.com/repos/evdokimenkoiv/FreeNETvpn/commits/$ref" -o "$stage/commit.json"
sha="$(python3 -c 'import json,re,sys; s=json.load(open(sys.argv[1]))["sha"]; assert re.fullmatch("[0-9a-f]{40}",s); print(s)' "$stage/commit.json")"
curl -fsSL --retry 3 --connect-timeout 15 --max-time 120 "https://raw.githubusercontent.com/evdokimenkoiv/FreeNETvpn/$sha/tools/update.py" -o "$stage/update.py"
trap - ERR
python3 "$stage/update.py" --root "$root" --ref "$sha" "$@"
