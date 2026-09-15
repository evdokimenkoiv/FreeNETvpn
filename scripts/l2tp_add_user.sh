#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
manage client add l2tp "${1:?Usage: bash scripts/l2tp_add_user.sh NAME}"
