#!/usr/bin/env bash
# Exercise the actual health-check control flow using disposable service/curl fixtures.
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/bin" "$scratch/tools" "$scratch/scripts"
cp "$root/tools/diagnostics.py" "$scratch/tools/"
cp "$root/scripts/health_check.sh" "$root/scripts/common.sh" "$scratch/scripts/"
printf 'SECRET_SENTINEL\n' >"$scratch/.env"
cat >"$scratch/tools/manage.py" <<'PY'
import os, sys
def read_config(root):
    return dict(DOMAIN='vpn.example.test', WG_DOMAIN='wg.example.test', COMPOSE_PROFILES='wireguard,vless')
if __name__ == '__main__':
    args = sys.argv[1:]
    if args[0] == 'get':
        print(read_config(None)[args[1]])
    elif args[:2] == ['compose', 'config']:
        print('caddy\nadmin')
    elif args[:2] == ['compose', 'ps']:
        print('caddy' if os.environ['MODE'] == 'stopped' else 'caddy\nadmin')
    elif args[0] == 'check-protocols' and os.environ['MODE'] == 'protocol':
        sys.exit(1)
PY
cat >"$scratch/bin/curl" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail
output=/dev/null
url="${!#}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) output="$2"; shift ;;
    -k|--insecure) echo 'TLS bypass attempted'; exit 99 ;;
  esac
  shift
done
printf 'SECRET_SENTINEL\n' >&2
if [[ "$url" == */healthz ]]; then
  case "$MODE" in
    dns) printf 000; exit 6 ;;
    connect) printf 000; exit 7 ;;
    timeout) printf 000; exit 28 ;;
    tls) printf 000; exit 60 ;;
    backend) printf 503; exit 0 ;;
    body) printf '<html>wrong site</html>' >"$output"; printf 200; exit 0 ;;
  esac
  printf '{"status":"ok"}' >"$output"
  printf 200
elif [[ "$MODE" == auth && "$url" == */admin ]] || [[ "$MODE" == wgauth && "$url" == https://wg.* ]]; then
  printf 200
else
  printf 401
fi
CURL
printf '#!/usr/bin/env bash\nexit 0\n' >"$scratch/bin/sleep"
chmod +x "$scratch/bin/"*
export PATH="$scratch/bin:$PATH" FREENET_LANG=en
for pair in dns:HTTPS_DNS connect:HTTPS_CONNECT timeout:HTTPS_TIMEOUT tls:HTTPS_TLS backend:HTTPS_BACKEND body:HTTPS_RESPONSE auth:HTTPS_AUTH wgauth:HTTPS_AUTH stopped:SERVICE_STOPPED protocol:INSTALL_STAGE; do
  export MODE="${pair%%:*}"
  if bash "$scratch/scripts/health_check.sh" --no-firewall >"$scratch/result" 2>&1; then
    echo "Failure incorrectly accepted: $MODE"; exit 1
  fi
  grep -Fq "[${pair#*:}]" "$scratch/result"
  grep -Fq 'sudo bash install.sh --existing --no-firewall' "$scratch/result"
  if grep -Fq SECRET_SENTINEL "$scratch/result"; then
    echo 'Private output leaked'; exit 1
  fi
  [[ "$(cat "$scratch/.env")" == SECRET_SENTINEL ]]
done
MODE=success bash "$scratch/scripts/health_check.sh" -q
echo 'PASS: DNS/connection/timeout/TLS/backend/body/auth/service/protocol failures, safe resume and success'
