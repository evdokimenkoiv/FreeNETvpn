#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
while true; do
  printf '\nFreeNETvpn\n1) WireGuard clients / Клиенты\n2) VLESS profile / Профиль\n3) Backup / Резервная копия\n4) Health / Проверка\n5) Diagnostics / Журналы\n6) Exit / Выход\n7) IKEv2 / L2TP / Outline / AmneziaWG clients\n'
  read -rp 'Choice / Выбор: ' choice
  case "$choice" in
    1) bash scripts/gen_wg_client.sh ;;
    2) bash scripts/gen_vless_client.sh ;;
    3) bash scripts/backup.sh ;;
    4) bash scripts/health_check.sh ;;
    5) bash scripts/diagnostics.sh ;;
    6) exit 0 ;;
    7)
      read -rp 'Protocol (ikev2/l2tp/outline/amnezia): ' protocol
      read -rp 'Action (add/list/export/revoke): ' action
      if [[ "$action" == list ]]; then
        python3 tools/manage.py client list "$protocol"
      else
        read -rp 'Client name: ' client_name
        python3 tools/manage.py client "$action" "$protocol" "$client_name"
      fi
      ;;
    *) echo "Choose 1-7" ;;
  esac
done
