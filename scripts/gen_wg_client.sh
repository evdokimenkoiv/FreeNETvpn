#!/usr/bin/env bash
set -euo pipefail
NAME=${1:-client-$(date +%s)}
CID=$(docker ps --format '{{.Names}}' | grep wg-easy || true)
if [[ -z "$CID" ]]; then echo "wg-easy is not running"; exit 1; fi
echo "Create via wg-easy UI at /wg (recommended). If CLI is supported by your image, run inside container."
