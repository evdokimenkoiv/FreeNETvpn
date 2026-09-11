#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ ${EUID} -eq 0 ]] || { echo "Run as root"; exit 1; }
[[ "${1:-}" == --confirm ]] || {
  echo "Rotation disconnects current VLESS clients. Use --confirm to back up and rotate."; exit 1;
}
manage rotate-vless
