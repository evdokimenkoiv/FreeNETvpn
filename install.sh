#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -ne 0 ]] && { echo "Run as root / Запустите с sudo"; exit 1; }

PS3="Select language / Выберите язык: "
select opt in "English" "Русский"; do
  case $REPLY in 1) LANG=EN; break;; 2) LANG=RU; break;; esac
done

msg(){ if [[ "$LANG" == "RU" ]]; then case "$1" in
  ask_domain) echo -n "Введите FQDN (напр., vpn.example.com): ";;
  ask_email) echo -n "E-mail для Let's Encrypt (prod): ";;
  ask_admin) echo -n "Логин администратора веб-панели: ";;
  ask_pass)  echo -n "Пароль администратора веб-панели: ";;
  ask_services) echo "Сервисы (по умолчанию: все). Через пробел: [ipsec l2tp wireguard outline vless amnezia all]";;
  ipv6_yes) echo "Обнаружен IPv6. Включить IPv6? [Y/n] ";;
  ipv6_no)  echo "IPv6 не найден. Включить IPv6? [y/N] ";;
  wg_ask) echo "Порт WireGuard: 1) 51820  2) свой  3) случайный";;
  ssh_hard) echo "Усилить SSH (смена порта, запрет паролей, fail2ban, UFW)? [Y/n] ";;
  ssh_2fa)  echo "Включить 2FA для SSH (Google Authenticator)? [y/N] ";;
  done) echo "Готово! Откройте https://$DOMAIN/ (панель).";;
esac; else case "$1" in
  ask_domain) echo -n "Enter FQDN (e.g., vpn.example.com): ";;
  ask_email) echo -n "E-mail for Let's Encrypt (prod): ";;
  ask_admin) echo -n "Admin login for web panel: ";;
  ask_pass)  echo -n "Admin password for web panel: ";;
  ask_services) echo "Services (default: all). Space-separated: [ipsec l2tp wireguard outline vless amnezia all]";;
  ipv6_yes) echo "IPv6 detected. Enable IPv6? [Y/n] ";;
  ipv6_no)  echo "No IPv6. Enable IPv6 anyway? [y/N] ";;
  wg_ask) echo "WireGuard port: 1) 51820  2) custom  3) random";;
  ssh_hard) echo "Harden SSH (change port, disable password, fail2ban, UFW)? [Y/n] ";;
  ssh_2fa)  echo "Enable SSH 2FA (Google Authenticator)? [y/N] ";;
  done) echo "Done! Open https://$DOMAIN/ (panel).";;
esac; fi }

read -rp "$(msg ask_domain)" DOMAIN
read -rp "$(msg ask_email)"  LE_EMAIL
read -rp "$(msg ask_admin)"  ADMIN_USER
read -rsp "$(msg ask_pass)"  ADMIN_PASS; echo
read -rp "$(msg ask_services) " SERVICES
[[ -z "${SERVICES:-}" || "${SERVICES}" == "all" ]] && SERVICES="ipsec l2tp wireguard outline vless amnezia"

apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release jq ufw fail2ban whiptail unzip sed grep iproute2

# Public IP & DNS check
bash scripts/check_public_ip.sh "$DOMAIN" || echo "Warning: public IP / DNS mismatch."

# Docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# IPsec/L2TP
if [[ "$SERVICES" == *"ipsec"* ]]; then apt-get install -y strongswan strongswan-pki; fi
if [[ "$SERVICES" == *"l2tp"* ]]; then apt-get install -y xl2tpd ppp; fi

# .env
cp .env.example .env
sed -i "s|^DOMAIN=.*|DOMAIN=${DOMAIN}|" .env
sed -i "s|^LE_EMAIL=.*|LE_EMAIL=${LE_EMAIL}|" .env
sed -i "s|^ADMIN_USER=.*|ADMIN_USER=${ADMIN_USER}|" .env
sed -i "s|^ADMIN_PASS=.*|ADMIN_PASS=${ADMIN_PASS}|" .env
sed -i "s|^SERVICES=.*|SERVICES=${SERVICES}|" .env

# IPv6
if ip -6 addr show scope global | grep -q inet6; then read -rp "$(msg ipv6_yes)" yn; [[ -z "$yn" || "$yn" =~ ^[Yy]$ ]] && ENABLE_IPV6=true || ENABLE_IPV6=false
else read -rp "$(msg ipv6_no)" yn; [[ "$yn" =~ ^[Yy]$ ]] && ENABLE_IPV6=true || ENABLE_IPV6=false
fi
sed -i "s|^ENABLE_IPV6=.*|ENABLE_IPV6=${ENABLE_IPV6}|" .env

# WG port
echo "$(msg wg_ask)"; read -r P
WG_PORT=51820
if [[ "$P" == "2" ]]; then read -rp "Enter UDP port (1024-65535): " WG_PORT
elif [[ "$P" == "3" ]]; then WG_PORT=$(shuf -i 20000-60000 -n 1)
fi
sed -i "s|^WG_PORT=.*|WG_PORT=${WG_PORT}|" .env

# Security
ufw --force enable || true
bash scripts/ufw_open_ports.sh "$SERVICES" "$WG_PORT"
read -rp "$(msg ssh_hard)" yn
if [[ -z "$yn" || "$yn" =~ ^[Yy]$ ]]; then
  NEWP=$(shuf -i 2201-2299 -n 1)
  sed -i "s/^#\\?Port .*/Port ${NEWP}/" /etc/ssh/sshd_config
  sed -i "s/^#\\?PasswordAuthentication .*/PasswordAuthentication no/" /etc/ssh/sshd_config
  ufw allow ${NEWP}/tcp
  systemctl restart ssh || systemctl restart sshd || true
  echo "SSH hardened. New port: ${NEWP}"
fi

read -rp "$(msg ssh_2fa)" yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
  apt-get install -y libpam-google-authenticator
  cp /etc/pam.d/sshd /etc/pam.d/sshd.bak.$(date +%s)
  echo "auth required pam_google_authenticator.so nullok" >> /etc/pam.d/sshd
  sed -i "s/^#\\?ChallengeResponseAuthentication .*/ChallengeResponseAuthentication yes/" /etc/ssh/sshd_config
  systemctl restart ssh || systemctl restart sshd || true
  echo "2FA enabled. Run 'google-authenticator' per user to enroll."
fi

systemctl enable fail2ban && systemctl restart fail2ban || true

# Prepare services (build admin, generate VLESS UUID if empty)
bash scripts/enable_services.sh "$SERVICES"

# Bring up docker stack
docker compose up -d

# IPsec PKI and configs
if [[ "$SERVICES" == *"ipsec"* ]]; then bash scripts/ipsec_init_pki.sh "$DOMAIN"; systemctl enable strongswan-starter && systemctl restart strongswan-starter; fi
if [[ "$SERVICES" == *"l2tp"* ]]; then systemctl enable xl2tpd && systemctl restart xl2tpd; fi

echo; msg done; echo
echo "Next: ./menu.sh  (create clients, backup, diagnostics)"
