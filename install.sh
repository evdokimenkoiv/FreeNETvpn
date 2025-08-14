#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (sudo). / Запустите с правами root (sudo)."
  exit 1
fi

# --- Language selection ---
PS3="Select language / Выберите язык: "
select opt in "English" "Русский"; do
  case $REPLY in
    1) LANG_CH=EN; break;;
    2) LANG_CH=RU; break;;
  esac
done

msg() {
  if [[ "${LANG_CH}" == "RU" ]]; then
    case "$1" in
      ask_domain) echo -n "Введите FQDN (например, vpn.example.com): ";;
      ask_email) echo -n "E-mail для Let's Encrypt (prod): ";;
      ask_admin) echo -n "Логин администратора веб-панели: ";;
      ask_pass)  echo -n "Пароль администратора веб-панели: ";;
      ask_services) echo "Выберите сервисы (по умолчанию: все). Введите через пробел: [ipsec l2tp wireguard outline vless amnezia all]";;
      ipv6_detect_yes) echo "Обнаружен адрес IPv6. Включить поддержку IPv6? [Y/n] ";;
      ipv6_detect_no) echo "IPv6 не обнаружен. Включить поддержку IPv6? (рекомендуется: n) [y/N] ";;
      wg_port_ask) echo "Порт WireGuard: [1] по умолчанию 51820, [2] задать свой, [3] случайный допустимый";;
      ssh_hardening) echo "Усилить SSH (сменить порт, запретить парольный вход, включить fail2ban и UFW)? [Y/n] ";;
      need_public_ip) echo "Внимание: у сервера нет белого IP или домен не указывает на этот IP. Установка продолжится, но часть сервисов может быть недоступна извне.";;
      done) echo "Готово! Откройте https://$DOMAIN/ для доступа к панели.";;
    esac
  else
    case "$1" in
      ask_domain) echo -n "Enter FQDN (e.g., vpn.example.com): ";;
      ask_email) echo -n "E-mail for Let's Encrypt (prod): ";;
      ask_admin) echo -n "Admin login for web panel: ";;
      ask_pass)  echo -n "Admin password for web panel: ";;
      ask_services) echo "Select services (default: all). Space-separated: [ipsec l2tp wireguard outline vless amnezia all]";;
      ipv6_detect_yes) echo "IPv6 address detected. Enable IPv6? [Y/n] ";;
      ipv6_detect_no) echo "No IPv6 detected. Enable IPv6? (recommended: n) [y/N] ";;
      wg_port_ask) echo "WireGuard port: [1] default 51820, [2] custom, [3] random allowed";;
      ssh_hardening) echo "Harden SSH (change port, disable password login, enable fail2ban & UFW)? [Y/n] ";;
      need_public_ip) echo "Warning: No public IP or domain doesn't resolve to this host. Installation continues but services may be unreachable.";;
      done) echo "Done! Open https://$DOMAIN/ to access the panel.";;
    esac
  fi
}

read -rp "$(msg ask_domain)" DOMAIN
read -rp "$(msg ask_email)"  LE_EMAIL
read -rp "$(msg ask_admin)"  ADMIN_USER
read -rsp "$(msg ask_pass)"  ADMIN_PASS; echo
read -rp "$(msg ask_services) " SERVICES
[[ -z "${SERVICES:-}" || "${SERVICES}" == "all" ]] && SERVICES="ipsec l2tp wireguard outline vless amnezia"

# --- Basic deps ---
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release jq ufw fail2ban whiptail unzip

# --- Check public IP & DNS ---
bash scripts/check_public_ip.sh "$DOMAIN" || msg need_public_ip

# --- Docker ---
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# --- strongSwan / L2TP ---
if [[ "$SERVICES" == *"ipsec"* ]]; then apt-get install -y strongswan; fi
if [[ "$SERVICES" == *"l2tp"* ]]; then apt-get install -y xl2tpd ppp; fi

# --- .env ---
cp .env.example .env
sed -i "s|^DOMAIN=.*|DOMAIN=${DOMAIN}|" .env
sed -i "s|^LE_EMAIL=.*|LE_EMAIL=${LE_EMAIL}|" .env
sed -i "s|^ADMIN_USER=.*|ADMIN_USER=${ADMIN_USER}|" .env
sed -i "s|^ADMIN_PASS=.*|ADMIN_PASS=${ADMIN_PASS}|" .env
sed -i "s|^SERVICES=.*|SERVICES=${SERVICES}|" .env

# IPv6 autodetect + ask
if ip -6 addr show scope global | grep -q "inet6"; then
  read -rp "$(msg ipv6_detect_yes)" yn
  [[ -z "$yn" || "$yn" =~ ^[Yy]$ ]] && ENABLE_IPV6=true || ENABLE_IPV6=false
else
  read -rp "$(msg ipv6_detect_no)" yn
  [[ "$yn" =~ ^[Yy]$ ]] && ENABLE_IPV6=true || ENABLE_IPV6=false
fi
sed -i "s|^ENABLE_IPV6=.*|ENABLE_IPV6=${ENABLE_IPV6}|" .env

# WireGuard port
echo "$(msg wg_port_ask)"
read -r WG_OPT
WG_PORT=51820
if [[ "${WG_OPT}" == "2" ]]; then
  read -rp "Enter custom UDP port (1024-65535): " WG_PORT
elif [[ "${WG_OPT}" == "3" ]]; then
  WG_PORT=$(shuf -i 20000-60000 -n 1)
fi
sed -i "s|^WG_PORT=.*|WG_PORT=${WG_PORT}|" .env

# --- Security: UFW + fail2ban + SSH hardening ---
ufw --force enable || true
bash scripts/ufw_open_ports.sh "$SERVICES" "$WG_PORT"

read -rp "$(msg ssh_hardening)" yn
if [[ -z "$yn" || "$yn" =~ ^[Yy]$ ]]; then
  NEW_SSH_PORT=$(shuf -i 2201-2299 -n 1)
  sed -i "s/^#\?Port .*/Port ${NEW_SSH_PORT}/" /etc/ssh/sshd_config
  sed -i "s/^#\?PasswordAuthentication .*/PasswordAuthentication no/" /etc/ssh/sshd_config
  ufw allow ${NEW_SSH_PORT}/tcp
  systemctl restart ssh || systemctl restart sshd || true
  echo "SSH hardened. New port: ${NEW_SSH_PORT}"
fi

systemctl enable fail2ban && systemctl restart fail2ban || true

# --- Enable services config ---
bash scripts/enable_services.sh "$SERVICES"

# --- Launch docker stack ---
docker compose up -d

# --- strongSwan/L2TP ---
if [[ "$SERVICES" == *"ipsec"* ]]; then
  systemctl enable strongswan-starter && systemctl restart strongswan-starter
fi
if [[ "$SERVICES" == *"l2tp"* ]]; then
  systemctl enable xl2tpd && systemctl restart xl2tpd
fi

echo
msg done
echo
echo "Next steps:"
echo " - /admin: web panel (BasicAuth)"
echo " - Run ./menu.sh for advanced options (client creation, backups, etc.)"
