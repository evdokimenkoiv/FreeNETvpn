#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
echo "Create/download clients and QR codes at https://$(manage get WG_DOMAIN)/"
echo "During initial setup use endpoint $(manage get DOMAIN) and UDP port $(manage get WG_PORT)."
