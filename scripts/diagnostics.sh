#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
manage compose ps
manage compose logs --tail 60 caddy admin
echo "For client traffic tests see docs/acceptance.md."
