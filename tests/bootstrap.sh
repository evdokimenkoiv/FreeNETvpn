#!/usr/bin/env bash
# Exercise the downloaded entry point without apt, Docker, networking or VPS changes.
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ ${EUID} -eq 0 ]] || { echo 'Run this disposable bootstrap test with sudo'; exit 1; }
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/bin" "$scratch/entry" "$scratch/package/repository/tools"
cp "$root/install.sh" "$scratch/entry/install.sh"
touch "$scratch/package/repository/tools/manage.py"
cat >"$scratch/package/repository/install.sh" <<'CHILD'
#!/usr/bin/env bash
set -euo pipefail
read -r answer
[[ "$answer" == vpn.example.test ]]
[[ "${1:-}" == --existing || "${CANONICAL_TEST:-0}" == 1 ]]
printf '%s\n' "$FREENET_REF" >"$(dirname -- "${BASH_SOURCE[0]}")/selected-ref"
echo 'PASS: complete checkout executed with arguments and interactive stdin preserved'
CHILD
tar -czf "$scratch/project.tar.gz" -C "$scratch/package" repository
cat >"$scratch/bin/apt-get" <<'APT'
#!/usr/bin/env bash
exit 0
APT
cat >"$scratch/bin/curl" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail
[[ "${MOCK_FAIL:-0}" == 0 ]] || exit 22
if [[ "$*" == *"/tarball/${FREENET_REF}"* ]]; then
  source_file="$MOCK_ARCHIVE"
elif [[ "$*" == *"/${FREENET_REF}/install.sh"* ]]; then
  source_file="$MOCK_ENTRY"
else
  exit 23
fi
while [[ "$1" != -o ]]; do shift; done
cp "$source_file" "$2"
CURL
chmod +x "$scratch/bin/apt-get" "$scratch/bin/curl"
export PATH="$scratch/bin:$PATH" MOCK_ARCHIVE="$scratch/project.tar.gz" FREENET_REF=test-reviewed-ref
export MOCK_ENTRY="$scratch/entry/install.sh"
export INSTALL_DIR="$scratch/deployed"
if MOCK_FAIL=1 bash "$scratch/entry/install.sh" --existing; then
  echo 'Failed download incorrectly succeeded'; exit 1
fi
[[ ! -e "$INSTALL_DIR" ]]
[[ -z "$(find "$scratch" -maxdepth 1 -name 'deployed.download.*' -print)" ]]
printf 'vpn.example.test\n' | bash "$scratch/entry/install.sh" --existing
[[ "$(cat "$INSTALL_DIR/selected-ref")" == test-reviewed-ref ]]
printf 'vpn.example.test\n' | MOCK_FAIL=1 bash "$scratch/entry/install.sh" --existing
mkdir "$scratch/unrelated"
printf 'preserve me' >"$scratch/unrelated/sentinel"
if INSTALL_DIR="$scratch/unrelated" bash "$scratch/entry/install.sh"; then
  echo 'Unrelated target incorrectly overwritten'; exit 1
fi
[[ "$(cat "$scratch/unrelated/sentinel")" == 'preserve me' ]]
if FREENET_REF='invalid;ref' INSTALL_DIR="$scratch/invalid" bash "$scratch/entry/install.sh"; then
  echo 'Invalid reference incorrectly accepted'; exit 1
fi
echo 'PASS: bootstrap retry, reference selection, reuse and non-overwriting guards'
# Execute the exact README command body with only apt/curl replaced by fixtures.
# The test is already root, so it omits sudo itself (which resets fixture PATH).
python3 - "$root/README.md" "$scratch/readme-command.sh" <<'PY'
import pathlib, shlex, sys
text = pathlib.Path(sys.argv[1]).read_text()
command = text.split('```bash\n', 1)[1].split('\n```', 1)[0]
parts = shlex.split(command)
assert parts[:3] == ['sudo', 'bash', '-c'] and len(parts) == 4
pathlib.Path(sys.argv[2]).write_text(parts[3])
PY
printf 'vpn.example.test\n' | INSTALL_DIR="$scratch/from-readme" CANONICAL_TEST=1 bash "$scratch/readme-command.sh"
[[ "$(cat "$scratch/from-readme/selected-ref")" == codex/freenetvpn-reliability ]]
echo 'PASS: exact one-command README bootstrap preserves interactive stdin'
