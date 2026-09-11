#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
while true; do
  printf '\nFreeNETvpn\n1) WireGuard clients / Клиенты\n2) VLESS profile / Профиль\n3) Backup / Резервная копия\n4) Health / Проверка\n5) Diagnostics / Журналы\n6) Exit / Выход\n'
  read -rp 'Choice / Выбор: ' choice
  case "$choice" in
    1) bash scripts/gen_wg_client.sh ;;
    2) bash scripts/gen_vless_client.sh ;;
    3) bash scripts/backup.sh ;;
    4) bash scripts/health_check.sh ;;
    5) bash scripts/diagnostics.sh ;;
    6) exit 0 ;;
    *) echo "Choose 1-6" ;;
  esac
done
