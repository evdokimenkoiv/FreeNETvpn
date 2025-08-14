#!/usr/bin/env bash
set -euo pipefail
DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2)
read -rp "Username (EAP): " U
read -rp "VPN Display Name (default: FreeNETvpn IKEv2): " NAME
NAME=${NAME:-FreeNETvpn IKEv2}
CA_PATH="/etc/ipsec.d/cacerts/caCert.pem"
if [[ ! -f "$CA_PATH" ]]; then echo "CA not found. Run scripts/ipsec_init_pki.sh first."; exit 1; fi
UUID1=$(cat /proc/sys/kernel/random/uuid)
UUID2=$(cat /proc/sys/kernel/random/uuid)

# Build mobileconfig
OUT="services/ikev2/${U}-${DOMAIN}.mobileconfig"
mkdir -p services/ikev2
CA_BASE64=$(base64 -w0 "$CA_PATH")
cat > "$OUT" <<CFG
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>PayloadContent</key><array>
    <dict>
      <key>PayloadCertificateFileName</key><string>FreeNETvpn-CA.cer</string>
      <key>PayloadContent</key><data>${CA_BASE64}</data>
      <key>PayloadDescription</key><string>Installs FreeNETvpn root CA</string>
      <key>PayloadDisplayName</key><string>FreeNETvpn CA</string>
      <key>PayloadIdentifier</key><string>com.freenetvpn.ca</string>
      <key>PayloadType</key><string>com.apple.security.root</string>
      <key>PayloadUUID</key><string>${UUID1}</string>
      <key>PayloadVersion</key><integer>1</integer>
    </dict>
    <dict>
      <key>PayloadDescription</key><string>${NAME}</string>
      <key>PayloadDisplayName</key><string>${NAME}</string>
      <key>PayloadIdentifier</key><string>com.freenetvpn.ikev2</string>
      <key>PayloadType</key><string>com.apple.vpn.managed</string>
      <key>PayloadUUID</key><string>${UUID2}</string>
      <key>PayloadVersion</key><integer>1</integer>
      <key>UserDefinedName</key><string>${NAME}</string>
      <key>VPNType</key><string>IKEv2</string>
      <key>Proxies</key><dict/>
      <key>IKEv2</key><dict>
        <key>AuthenticationMethod</key><string>None</string>
        <key>ChildSecurityAssociationParameters</key><dict>
          <key>EncryptionAlgorithm</key><string>AlgorithmAES-256-GCM</string>
          <key>IntegrityAlgorithm</key><string>SHA2-256</string>
          <key>DiffieHellmanGroup</key><integer>14</integer>
        </dict>
        <key>DeadPeerDetectionRate</key><string>Medium</string>
        <key>DisableMOBIKE</key><integer>0</integer>
        <key>DisableRedirect</key><integer>0</integer>
        <key>EnablePFS</key><integer>1</integer>
        <key>LocalIdentifierType</key><string>KeyID</string>
        <key>RemoteAddress</key><string>${DOMAIN}</string>
        <key>RemoteIdentifier</key><string>${DOMAIN}</string>
        <key>UseConfigurationAttributeInternalIPSubnet</key><integer>1</integer>
        <key>ExtendedAuthEnabled</key><integer>1</integer>
        <key>PayloadCertificateUUID</key><string>${UUID1}</string>
        <key>AuthName</key><string>${U}</string>
      </dict>
    </dict>
  </array>
  <key>PayloadDisplayName</key><string>${NAME}</string>
  <key>PayloadIdentifier</key><string>com.freenetvpn.profile</string>
  <key>PayloadRemovalDisallowed</key><false/>
  <key>PayloadType</key><string>Configuration</string>
  <key>PayloadUUID</key><string>$(cat /proc/sys/kernel/random/uuid)</string>
  <key>PayloadVersion</key><integer>1</integer>
</dict></plist>
CFG
echo "Created: $OUT"
