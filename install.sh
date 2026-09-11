#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ ${EUID} -eq 0 ]] || { echo "Run with sudo bash install.sh"; exit 1; }
# The downloaded entry point obtains a complete checkout before using project files.
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "${source_dir}/tools/manage.py" ]]; then
  install_dir="${INSTALL_DIR:-/opt/freenetvpn}"
  if [[ -f "${install_dir}/tools/manage.py" ]]; then
    exec bash "${install_dir}/install.sh" "$@"
  fi
  if [[ -e "$install_dir" ]]; then
    echo "Refusing to overwrite existing directory: $install_dir"; exit 1
  fi
  ref="${FREENET_REF:-main}"
  [[ "$ref" =~ ^[a-zA-Z0-9._/-]+$ ]] || { echo "Invalid FREENET_REF"; exit 1; }
  apt-get update
  apt-get install -y ca-certificates curl
  mkdir -p "$install_dir"
  archive="$(mktemp)"
  trap 'rm -f -- "$archive"' EXIT
  curl --fail --location --retry 3 --connect-timeout 15 \
    "https://api.github.com/repos/evdokimenkoiv/FreeNETvpn/tarball/${ref}" -o "$archive"
  tar --extract --gzip --file "$archive" --strip-components=1 --directory "$install_dir"
  rm -f -- "$archive"
  trap - EXIT
  exec bash "${install_dir}/install.sh" "$@"
fi
cd "$source_dir"
# OS metadata is trusted system configuration; user .env is parsed as data in Python.
# shellcheck disable=SC1091
source /etc/os-release
[[ "$ID" == ubuntu && ( "$VERSION_ID" == 22.04 || "$VERSION_ID" == 24.04 ) ]] || {
  echo "Supported systems: Ubuntu 22.04 and 24.04 LTS"; exit 1;
}
existing=0
firewall=1
for argument in "$@"; do
  case "$argument" in
    --existing) existing=1 ;;
    --no-firewall) firewall=0 ;;
    *) echo "Usage: sudo bash install.sh [--existing] [--no-firewall]"; exit 1 ;;
  esac
done
apt-get update
apt-get install -y python3 ca-certificates curl gnupg ufw
if [[ $existing -eq 1 ]]; then
  python3 tools/manage.py validate
  python3 tools/manage.py render
else
  python3 tools/manage.py configure
fi
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
    "$(dpkg --print-architecture)" "$VERSION_CODENAME" >/etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker
profiles="$(python3 tools/manage.py get COMPOSE_PROFILES)"
if [[ ",$profiles," == *,wireguard,* ]]; then
  modprobe wireguard
fi
python3 tools/manage.py compose config --quiet
python3 tools/manage.py compose pull --ignore-buildable
python3 tools/manage.py compose build --pull admin
python3 tools/manage.py compose run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
if [[ ",$profiles," == *,vless,* ]]; then
  python3 tools/manage.py compose run --rm --no-deps xray run -test -config /etc/xray/config.json
fi
if [[ $firewall -eq 1 ]]; then
  bash scripts/ufw_open_ports.sh
fi
# Bind-mounted config files need container recreation after atomic file replacement.
python3 tools/manage.py compose up -d --force-recreate --wait --wait-timeout 120
bash scripts/health_check.sh
domain="$(python3 tools/manage.py get DOMAIN)"
wg_domain="$(python3 tools/manage.py get WG_DOMAIN)"
echo "Panel ready: https://${domain}/admin"
if [[ ",$profiles," == *,wireguard,* ]]; then
  echo "Complete the WireGuard setup at https://${wg_domain}/ (endpoint: ${domain})."
  echo "Set the WireGuard port to $(python3 tools/manage.py get WG_PORT) and DNS to the values in .env."
fi
echo "Verify a VPN client handshake and traffic before treating the server as operational."
