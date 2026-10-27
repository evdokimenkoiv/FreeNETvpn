#!/usr/bin/env bash
# Run the exact documented update bootstrap without networking or host mutations.
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ ${EUID} -eq 0 ]] || { echo 'Run this disposable fixture with sudo'; exit 1; }
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/bin" "$scratch/installation/tools"
touch "$scratch/installation/tools/manage.py"
printf 'preserved settings' >"$scratch/installation/.env"
cat >"$scratch/updater.py" <<'PY'
import os, pathlib, sys
args = sys.argv[1:]
assert args == ['--root', os.environ['INSTALL_DIR'], '--ref', 'a' * 40]
assert pathlib.Path(os.environ['INSTALL_DIR'], '.env').read_text() == 'preserved settings'
print('PASS: pinned updater received the existing installation without resetting settings')
PY
cat >"$scratch/bin/curl" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail
[[ "${FAIL_FETCH:-0}" == 0 ]] || exit 22
url=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    https://*) url="$1" ;;
    -o) output="$2"; shift ;;
  esac
  shift
done
case "$url" in
  */main/update.sh) cp "$FIXTURE_ROOT/update.sh" "$output" ;;
  */commits/main) printf '{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}' >"$output" ;;
  */aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/tools/update.py) cp "$MOCK_UPDATER" "$output" ;;
  *) exit 23 ;;
esac
CURL
chmod +x "$scratch/bin/curl"
export PATH="$scratch/bin:$PATH" FIXTURE_ROOT="$root" MOCK_UPDATER="$scratch/updater.py" INSTALL_DIR="$scratch/installation"
python3 - "$root/docs/update.en.md" "$root/docs/update.ru.md" "$scratch/command.sh" <<'PY'
import pathlib, shlex, sys
commands = [pathlib.Path(p).read_text().split('```bash\n',1)[1].split('\n```',1)[0] for p in sys.argv[1:3]]
assert commands[0] == commands[1]
parts = shlex.split(commands[0])
assert parts[:3] == ['sudo','bash','-c'] and len(parts) == 4
pathlib.Path(sys.argv[3]).write_text(parts[3])
PY
bash "$scratch/command.sh"
[[ "$(cat "$INSTALL_DIR/.env")" == 'preserved settings' ]]
cp "$root/update.sh" "$scratch/downloaded-entry.sh"
if FAIL_FETCH=1 bash "$scratch/downloaded-entry.sh" >"$scratch/error" 2>&1; then
  echo 'Failed download incorrectly accepted'; exit 1
fi
grep -Fq '[UPDATE_DOWNLOAD]' "$scratch/error"
[[ "$(cat "$INSTALL_DIR/.env")" == 'preserved settings' ]]
echo 'PASS: exact bilingual one-command update and safe download failure'
