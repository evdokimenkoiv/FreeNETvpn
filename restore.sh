#!/usr/bin/env bash
set -Eeuo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Run as root"; exit 1; }
[[ $# -eq 1 ]] || { echo "Usage: sudo bash restore.sh /absolute/path/backup.tar.gz"; exit 1; }
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 "$root/tools/manage.py" restore "$1"
