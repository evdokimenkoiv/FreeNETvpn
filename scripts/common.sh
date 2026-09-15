#!/usr/bin/env bash
# shellcheck shell=bash
set -Eeuo pipefail
FREENET_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$FREENET_ROOT"
manage() { python3 "$FREENET_ROOT/tools/manage.py" "$@"; }
