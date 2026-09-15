#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ ${EUID} -eq 0 ]] || { echo 'Run as root'; exit 1; }
# systemd requires escaped paths; reject unsupported installation locations.
[[ "$root" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo 'Use an installation path without spaces or special characters'; exit 1; }
cat >/etc/systemd/system/freenetvpn-control.service <<EOF
[Unit]
Description=FreeNETvpn restricted local control service
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${root}/tools/control_agent.py --root ${root}
WorkingDirectory=${root}
Restart=on-failure
RestartSec=3
UMask=0077
RuntimeDirectory=freenetvpn
RuntimeDirectoryMode=0755
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=${root}

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable freenetvpn-control.service
systemctl restart freenetvpn-control.service
