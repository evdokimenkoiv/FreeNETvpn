#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
[[ ${EUID} -eq 0 ]] || { echo "Run as root to read all VPN state"; exit 1; }
echo "Services pause briefly for a consistent backup, then resume."
manage backup
