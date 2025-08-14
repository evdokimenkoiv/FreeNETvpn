#!/usr/bin/env bash
set -euo pipefail
while true; do
  echo "=== FreeNETvpn Control Panel ==="
  echo "1) Create WireGuard client"
  echo "2) Create VLESS client"
  echo "3) Rotate VLESS UUID & path"
  echo "4) Add IKEv2 user"
  echo "5) Generate IKEv2 .mobileconfig"
  echo "6) Add L2TP user"
  echo "7) Create backup"
  echo "8) Diagnostics"
  echo "9) Exit"
  read -rp "Choice: " c
  case "$c" in
    1) bash scripts/gen_wg_client.sh ;;
    2) bash scripts/gen_vless_client.sh ;;
    3) bash scripts/rotate_vless.sh ;;
    4) bash scripts/ikev2_add_user.sh ;;
    5) bash scripts/ikev2_mobileconfig.sh ;;
    6) bash scripts/l2tp_add_user.sh ;;
    7) mkdir -p backups && tar czf backups/freenetvpn-backup-$(date +%s).tar.gz services host ;;
    8) bash scripts/health_check.sh ;;
    9) exit 0 ;;
  esac
done
