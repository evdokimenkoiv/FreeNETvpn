#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
manage client export ikev2 "${1:?Usage: bash scripts/ikev2_mobileconfig.sh NAME}"
