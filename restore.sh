#!/usr/bin/env bash
set -euo pipefail
ARCH="${1:-}"
[[ -z "$ARCH" || ! -f "$ARCH" ]] && { echo "Usage: ./restore.sh <backup-archive.tar.gz>"; exit 1; }
tar xzf "$ARCH"
echo "Restored services/ and host/. Review .env and run: docker compose up -d"
