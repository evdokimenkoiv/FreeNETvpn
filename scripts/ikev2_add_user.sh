#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
manage client add ikev2 "${1:?Usage: bash scripts/ikev2_add_user.sh NAME}"
