#!/usr/bin/env bash
set -euo pipefail

LANG_CH=${1:-EN}
read -rp "Language [EN/RU] (default EN): " tmp || true
[[ -n "${tmp:-}" ]] && LANG_CH="$tmp"

t() {
  if [[ "$LANG_CH" == "RU" ]]; then
    case "$1" in
      menu) echo "FreeNETvpn — Панель управления";;
      s1) echo "1) Создать клиента WireGuard";;
      s2) echo "2) Создать клиента VLESS";;
      s3) echo "3) Создать бэкап конфигов";;
      s4) echo "4) Диагностика";;
      s5) echo "5) Выход";;
      prompt) echo -n "Выбор: ";;
    esac
  else
    case "$1" in
      menu) echo "FreeNETvpn — Control Panel";;
      s1) echo "1) Create WireGuard client";;
      s2) echo "2) Create VLESS client";;
      s3) echo "3) Create configs backup";;
      s4) echo "4) Diagnostics";;
      s5) echo "5) Exit";;
      prompt) echo -n "Choice: ";;
    esac
  fi
}

while true; do
  echo "=== $(t menu) ==="
  echo "$(t s1)"
  echo "$(t s2)"
  echo "$(t s3)"
  echo "$(t s4)"
  echo "$(t s5)"
  read -rp "$(t prompt)" c
  case "$c" in
    1) bash scripts/gen_wg_client.sh ;;
    2) bash scripts/gen_vless_client.sh ;;
    3) mkdir -p backups && tar czf backups/freenetvpn-backup-$(date +%s).tar.gz services host ;;
    4) bash scripts/diagnostics.sh ;;
    5) exit 0 ;;
  esac
done
