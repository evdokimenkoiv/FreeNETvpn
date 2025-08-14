#!/usr/bin/env bash
set -euo pipefail
ARCH="${1:-}"
if [[ -z "$ARCH" || ! -f "$ARCH" ]]; then
  echo "Usage: ./restore.sh <backup-archive.tar.gz>"
  exit 1
fi
tar xzf "$ARCH"
echo "Restored services/ and host/ from backup. Adjust .env and run: docker compose up -d"
