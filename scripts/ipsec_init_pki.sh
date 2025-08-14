#!/usr/bin/env bash
set -euo pipefail
DOMAIN="${1:?domain required}"
mkdir -p /etc/ipsec.d/{cacerts,certs,private}
# CA
ipsec pki --gen --type rsa --size 4096 --outform pem > /etc/ipsec.d/private/caKey.pem
ipsec pki --self --ca --lifetime 3650 --in /etc/ipsec.d/private/caKey.pem --type rsa \
  --dn "CN=FreeNETvpn-CA" --outform pem > /etc/ipsec.d/cacerts/caCert.pem
# Server cert
ipsec pki --gen --type rsa --size 4096 --outform pem > /etc/ipsec.d/private/serverKey.pem
ipsec pki --pub --in /etc/ipsec.d/private/serverKey.pem --type rsa \
  | ipsec pki --issue --lifetime 1825 --cacert /etc/ipsec.d/cacerts/caCert.pem \
    --cakey /etc/ipsec.d/private/caKey.pem --dn "CN=${DOMAIN}" --san "${DOMAIN}" \
    --flag serverAuth --flag ikeIntermediate --outform pem > /etc/ipsec.d/certs/serverCert.pem
# DER for strongSwan
openssl x509 -in /etc/ipsec.d/certs/serverCert.pem -outform der -out /etc/ipsec.d/certs/serverCert.der
# Basic secrets/users file for EAP
touch /etc/ipsec.secrets
# Deploy configs from repo
cp host/ipsec/ipsec.conf /etc/ipsec.conf
cp host/ipsec/strongswan.conf /etc/strongswan.conf
systemctl restart strongswan-starter
echo "IPsec PKI initialized."
