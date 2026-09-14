# Device setup guides

[English](devices.en.md) · [Русский](devices.ru.md)

The same instructions are available in the portal under Setup guides. Your administrator must assign a profile first.

## iOS / iPadOS

### WireGuard

1. **Install WireGuard.** Use the official app list below and choose your platform.
2. **Get your profile.** Choose Get profile or the download button on the right. Save the .conf file.
3. **Add a tunnel.** Tap + in the app and import the .conf file, or scan its QR code from another screen. Allow the app to add a VPN configuration.
4. **Activate the connection.** Select and activate the imported tunnel. Do not use one profile on several devices at the same time.
5. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://www.wireguard.com/install/).

### VLESS

Your client must support the profile transport: WebSocket/TLS or gRPC/TLS. Use Xray JSON for mobile keep-alive settings; the URI/QR only carries standard WS/TLS.

1. **Choose an app.** Use the Project X list to choose a client for iOS or your macOS architecture with the required transport. App availability varies by region.
2. **Add the configuration.** Copy the vless:// profile and import from clipboard, or scan its QR code. Import Xray JSON as a configuration file in a client that supports it.
3. **Enable VPN or system proxy.** Select the profile and connect. On desktop, system proxy covers only compatible apps; full tunneling requires supported TUN/VPN mode. Keep TLS certificate verification enabled.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://xtls.github.io/en/document/level-0/ch08-xray-clients.html).

### IKEv2

Use your exported settings. Your VPN password may differ from your portal password.

1. **Download your settings.** Extract the ZIP. It contains JSON server/account settings, ca.pem and an Apple .mobileconfig.
2. **Create a VPN connection.** Open the .mobileconfig and approve installation in device profile settings. Confirm the CA came from your administrator before trusting it.
3. **Check the fields.** Server and Remote ID must match server/remote_id in the JSON. Use exported credentials, EAP-MSCHAPv2 and the trusted CA. On Windows, install the CA in the computer trusted root store following your organization’s policy.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://support.apple.com/guide/deployment/vpn-settings-overview-dep2d2adb35d/web).

### L2TP/IPsec

Use your exported settings. Your VPN password may differ from your portal password.

1. **Download your settings.** Open the JSON: server is the endpoint, username/password are the VPN account, and ipsec_psk is the IPsec shared secret.
2. **Create a VPN connection.** Open device VPN settings and add an L2TP/IPsec connection if your OS supports it.
3. **Check the fields.** Enter the server, username and password, and put ipsec_psk in the IPsec PSK/Shared secret field. Do not use unencrypted L2TP without IPsec.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://support.apple.com/guide/deployment/vpn-settings-overview-dep2d2adb35d/web).

### Outline

1. **Install Outline Client.** Use the official download link for your device. Members do not need Outline Manager.
2. **Add your key.** Copy ss:// from your profile. In Outline, add a server and paste the access key.
3. **Connect.** Choose Connect and approve the VPN permission if prompted.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://developer.getoutline.org/download-links/).

### AmneziaWG

Use an AmneziaWG client supporting S1–S4 and H1–H4. The standard WireGuard app is not compatible.

1. **Install a compatible client.** Use the official Amnezia website and check app compatibility with the exported profile.
2. **Import the file.** Download the .conf file and import it as a tunnel in AmneziaWG. On a phone, you can use the portal QR code.
3. **Connect.** Allow the VPN configuration and activate the tunnel. Reimport the profile after a preset change.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://docs.amnezia.org/documentation/instructions/use-amneziawg-app/).

### Telegram MTProto

MTProto works only in Telegram, not as a VPN for other apps. No router configuration is needed: add the proxy in Telegram on each device.

1. **Install Telegram.** Use the official Telegram app for iOS, Android, macOS or Windows. The web client does not use this profile.
2. **Open your profile link.** Copy the tg://proxy link from your assigned profile and open it on your device. Alternatively, find Proxy in Telegram settings, choose MTProto and enter server, port and secret from the link.
3. **Connect and verify.** Confirm proxy use. Wait for connection and check that messages and media load. Calls and other apps may use a different route. Keep the secret link private.

[Official guide / download](https://telegram.org/apps).

### HTTP / SOCKS5

HTTP CONNECT and SOCKS5 require a username and password; UDP is disabled. Proxy transport itself is unencrypted: use it over a VPN on untrusted networks. HTTPS keeps website content encrypted. Internal server addresses are blocked.

1. **Open the JSON.** server is the address; http_port is the HTTP port; socks5_port is the SOCKS5 port. username and password are proxy credentials, separate from your portal login.
2. **Choose where to configure it.** For HTTP: Settings → Wi-Fi → your network → Configure Proxy → Manual; enable authentication. This applies to that Wi-Fi network, not cellular data. Configure SOCKS5 in a compatible app.
3. **Test the application.** Open an HTTPS website and check the public IP in the configured app. For SOCKS5, enable proxy-side DNS if supported. An HTTP 407 response means you should check proxy credentials.

[Official guide / download](https://curl.se/docs/manpage.html).

## macOS

### WireGuard

1. **Install WireGuard.** Use the official app list below and choose your platform.
2. **Get your profile.** Choose Get profile or the download button on the right. Save the .conf file.
3. **Add a tunnel.** In WireGuard choose Import tunnel from file and select the .conf file. Allow the VPN interface when prompted.
4. **Activate the connection.** Select and activate the imported tunnel. Do not use one profile on several devices at the same time.
5. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://www.wireguard.com/install/).

### VLESS

Your client must support the profile transport: WebSocket/TLS or gRPC/TLS. Use Xray JSON for mobile keep-alive settings; the URI/QR only carries standard WS/TLS.

1. **Choose an app.** Use the Project X list to choose a client for iOS or your macOS architecture with the required transport. App availability varies by region.
2. **Add the configuration.** Copy the vless:// profile and import from clipboard, or scan its QR code. Import Xray JSON as a configuration file in a client that supports it.
3. **Enable VPN or system proxy.** Select the profile and connect. On desktop, system proxy covers only compatible apps; full tunneling requires supported TUN/VPN mode. Keep TLS certificate verification enabled.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://xtls.github.io/en/document/level-0/ch08-xray-clients.html).

### IKEv2

Use your exported settings. Your VPN password may differ from your portal password.

1. **Download your settings.** Extract the ZIP. It contains JSON server/account settings, ca.pem and an Apple .mobileconfig.
2. **Create a VPN connection.** Open the .mobileconfig and approve installation in device profile settings. Confirm the CA came from your administrator before trusting it.
3. **Check the fields.** Server and Remote ID must match server/remote_id in the JSON. Use exported credentials, EAP-MSCHAPv2 and the trusted CA. On Windows, install the CA in the computer trusted root store following your organization’s policy.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://support.apple.com/guide/deployment/vpn-settings-overview-dep2d2adb35d/web).

### L2TP/IPsec

Use your exported settings. Your VPN password may differ from your portal password.

1. **Download your settings.** Open the JSON: server is the endpoint, username/password are the VPN account, and ipsec_psk is the IPsec shared secret.
2. **Create a VPN connection.** Open device VPN settings and add an L2TP/IPsec connection if your OS supports it.
3. **Check the fields.** Enter the server, username and password, and put ipsec_psk in the IPsec PSK/Shared secret field. Do not use unencrypted L2TP without IPsec.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://support.apple.com/guide/deployment/vpn-settings-overview-dep2d2adb35d/web).

### Outline

1. **Install Outline Client.** Use the official download link for your device. Members do not need Outline Manager.
2. **Add your key.** Copy ss:// from your profile. In Outline, add a server and paste the access key.
3. **Connect.** Choose Connect and approve the VPN permission if prompted.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://developer.getoutline.org/download-links/).

### AmneziaWG

Use an AmneziaWG client supporting S1–S4 and H1–H4. The standard WireGuard app is not compatible.

1. **Install a compatible client.** Use the official Amnezia website and check app compatibility with the exported profile.
2. **Import the file.** Download the .conf file and import it as a tunnel in AmneziaWG. On a phone, you can use the portal QR code.
3. **Connect.** Allow the VPN configuration and activate the tunnel. Reimport the profile after a preset change.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://docs.amnezia.org/documentation/instructions/use-amneziawg-app/).

### Telegram MTProto

MTProto works only in Telegram, not as a VPN for other apps. No router configuration is needed: add the proxy in Telegram on each device.

1. **Install Telegram.** Use the official Telegram app for iOS, Android, macOS or Windows. The web client does not use this profile.
2. **Open your profile link.** Copy the tg://proxy link from your assigned profile and open it on your device. Alternatively, find Proxy in Telegram settings, choose MTProto and enter server, port and secret from the link.
3. **Connect and verify.** Confirm proxy use. Wait for connection and check that messages and media load. Calls and other apps may use a different route. Keep the secret link private.

[Official guide / download](https://telegram.org/apps).

### HTTP / SOCKS5

HTTP CONNECT and SOCKS5 require a username and password; UDP is disabled. Proxy transport itself is unencrypted: use it over a VPN on untrusted networks. HTTPS keeps website content encrypted. Internal server addresses are blocked.

1. **Open the JSON.** server is the address; http_port is the HTTP port; socks5_port is the SOCKS5 port. username and password are proxy credentials, separate from your portal login.
2. **Choose where to configure it.** System Settings → Network → your connection → Details → Proxies. Choose HTTP/HTTPS proxy with http_port or SOCKS with socks5_port and enter credentials. Authentication support depends on the app.
3. **Test the application.** Open an HTTPS website and check the public IP in the configured app. For SOCKS5, enable proxy-side DNS if supported. An HTTP 407 response means you should check proxy credentials.

[Official guide / download](https://curl.se/docs/manpage.html).

## Windows

### WireGuard

1. **Install WireGuard.** Use the official app list below and choose your platform.
2. **Get your profile.** Choose Get profile or the download button on the right. Save the .conf file.
3. **Add a tunnel.** In WireGuard choose Import tunnel from file and select the .conf file. Allow the VPN interface when prompted.
4. **Activate the connection.** Select and activate the imported tunnel. Do not use one profile on several devices at the same time.
5. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://www.wireguard.com/install/).

### VLESS

Your client must support the profile transport: WebSocket/TLS or gRPC/TLS. Use Xray JSON for mobile keep-alive settings; the URI/QR only carries standard WS/TLS.

1. **Choose an app.** For example, v2rayN from the official Project X list.
2. **Add the configuration.** Copy the vless:// profile and import from clipboard, or scan its QR code. Import Xray JSON as a configuration file in a client that supports it.
3. **Enable VPN or system proxy.** Select the profile and connect. On desktop, system proxy covers only compatible apps; full tunneling requires supported TUN/VPN mode. Keep TLS certificate verification enabled.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://xtls.github.io/en/document/level-0/ch08-xray-clients.html).

### IKEv2

Use your exported settings. Your VPN password may differ from your portal password.

1. **Download your settings.** Extract the ZIP. It contains JSON server/account settings, ca.pem and an Apple .mobileconfig.
2. **Create a VPN connection.** Settings → Network & Internet → VPN → Add VPN. Choose Windows built-in and the exact type: IKEv2 or L2TP/IPsec with a pre-shared key.
3. **Check the fields.** Server and Remote ID must match server/remote_id in the JSON. Use exported credentials, EAP-MSCHAPv2 and the trusted CA. On Windows, install the CA in the computer trusted root store following your organization’s policy.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://support.microsoft.com/en-us/windows/experience/connectivity-networking/connect-to-a-vpn-in-windows).

### L2TP/IPsec

Use your exported settings. Your VPN password may differ from your portal password.

1. **Download your settings.** Open the JSON: server is the endpoint, username/password are the VPN account, and ipsec_psk is the IPsec shared secret.
2. **Create a VPN connection.** Settings → Network & Internet → VPN → Add VPN. Choose Windows built-in and the exact type: IKEv2 or L2TP/IPsec with a pre-shared key.
3. **Check the fields.** Enter the server, username and password, and put ipsec_psk in the IPsec PSK/Shared secret field. Do not use unencrypted L2TP without IPsec.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://support.microsoft.com/en-us/windows/experience/connectivity-networking/connect-to-a-vpn-in-windows).

### Outline

1. **Install Outline Client.** Use the official download link for your device. Members do not need Outline Manager.
2. **Add your key.** Copy ss:// from your profile. In Outline, add a server and paste the access key.
3. **Connect.** Choose Connect and approve the VPN permission if prompted.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://developer.getoutline.org/download-links/).

### AmneziaWG

Use an AmneziaWG client supporting S1–S4 and H1–H4. The standard WireGuard app is not compatible.

1. **Install a compatible client.** Use the official Amnezia website and check app compatibility with the exported profile.
2. **Import the file.** Download the .conf file and import it as a tunnel in AmneziaWG. On a phone, you can use the portal QR code.
3. **Connect.** Allow the VPN configuration and activate the tunnel. Reimport the profile after a preset change.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://docs.amnezia.org/documentation/instructions/use-amneziawg-app/).

### Telegram MTProto

MTProto works only in Telegram, not as a VPN for other apps. No router configuration is needed: add the proxy in Telegram on each device.

1. **Install Telegram.** Use the official Telegram app for iOS, Android, macOS or Windows. The web client does not use this profile.
2. **Open your profile link.** Copy the tg://proxy link from your assigned profile and open it on your device. Alternatively, find Proxy in Telegram settings, choose MTProto and enter server, port and secret from the link.
3. **Connect and verify.** Confirm proxy use. Wait for connection and check that messages and media load. Calls and other apps may use a different route. Keep the secret link private.

[Official guide / download](https://telegram.org/apps).

### HTTP / SOCKS5

HTTP CONNECT and SOCKS5 require a username and password; UDP is disabled. Proxy transport itself is unencrypted: use it over a VPN on untrusted networks. HTTPS keeps website content encrypted. Internal server addresses are blocked.

1. **Open the JSON.** server is the address; http_port is the HTTP port; socks5_port is the SOCKS5 port. username and password are proxy credentials, separate from your portal login.
2. **Choose where to configure it.** Settings → Network & Internet → Proxy → manual setup for HTTP. Compatible apps prompt for credentials. Configure SOCKS5 and apps that ignore the system proxy separately.
3. **Test the application.** Open an HTTPS website and check the public IP in the configured app. For SOCKS5, enable proxy-side DNS if supported. An HTTP 407 response means you should check proxy credentials.

[Official guide / download](https://curl.se/docs/manpage.html).

## Android

### WireGuard

1. **Install WireGuard.** Use the official app list below and choose your platform.
2. **Get your profile.** Choose Get profile or the download button on the right. Save the .conf file.
3. **Add a tunnel.** Tap + in the app and import the .conf file, or scan its QR code from another screen. Allow the app to add a VPN configuration.
4. **Activate the connection.** Select and activate the imported tunnel. Do not use one profile on several devices at the same time.
5. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://www.wireguard.com/install/).

### VLESS

Your client must support the profile transport: WebSocket/TLS or gRPC/TLS. Use Xray JSON for mobile keep-alive settings; the URI/QR only carries standard WS/TLS.

1. **Choose an app.** For example, v2rayNG from the official Project X list.
2. **Add the configuration.** Copy the vless:// profile and import from clipboard, or scan its QR code. Import Xray JSON as a configuration file in a client that supports it.
3. **Enable VPN or system proxy.** Select the profile and connect. On desktop, system proxy covers only compatible apps; full tunneling requires supported TUN/VPN mode. Keep TLS certificate verification enabled.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://xtls.github.io/en/document/level-0/ch08-xray-clients.html).

### IKEv2

Use your exported settings. Your VPN password may differ from your portal password.

1. **Download your settings.** Extract the ZIP. It contains JSON server/account settings, ca.pem and an Apple .mobileconfig.
2. **Create a VPN connection.** In a compatible IKEv2 client such as strongSwan, create an IKEv2 EAP (username/password) profile and import the CA.
3. **Check the fields.** Server and Remote ID must match server/remote_id in the JSON. Use exported credentials, EAP-MSCHAPv2 and the trusted CA. On Windows, install the CA in the computer trusted root store following your organization’s policy.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://docs.strongswan.org/docs/latest/os/androidVpnClient.html).

### L2TP/IPsec

Many recent Android versions omit L2TP/IPsec. If it is unavailable, request an IKEv2, WireGuard or AmneziaWG profile; do not substitute a different protocol.

1. **Download your settings.** Open the JSON: server is the endpoint, username/password are the VPN account, and ipsec_psk is the IPsec shared secret.
2. **Create a VPN connection.** Open device VPN settings and add an L2TP/IPsec connection if your OS supports it.
3. **Check the fields.** Enter the server, username and password, and put ipsec_psk in the IPsec PSK/Shared secret field. Do not use unencrypted L2TP without IPsec.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://docs.strongswan.org/docs/latest/os/androidVpnClient.html).

### Outline

1. **Install Outline Client.** Use the official download link for your device. Members do not need Outline Manager.
2. **Add your key.** Copy ss:// from your profile. In Outline, add a server and paste the access key.
3. **Connect.** Choose Connect and approve the VPN permission if prompted.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://developer.getoutline.org/download-links/).

### AmneziaWG

Use an AmneziaWG client supporting S1–S4 and H1–H4. The standard WireGuard app is not compatible.

1. **Install a compatible client.** Use the official Amnezia website and check app compatibility with the exported profile.
2. **Import the file.** Download the .conf file and import it as a tunnel in AmneziaWG. On a phone, you can use the portal QR code.
3. **Connect.** Allow the VPN configuration and activate the tunnel. Reimport the profile after a preset change.
4. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://docs.amnezia.org/documentation/instructions/use-amneziawg-app/).

### Telegram MTProto

MTProto works only in Telegram, not as a VPN for other apps. No router configuration is needed: add the proxy in Telegram on each device.

1. **Install Telegram.** Use the official Telegram app for iOS, Android, macOS or Windows. The web client does not use this profile.
2. **Open your profile link.** Copy the tg://proxy link from your assigned profile and open it on your device. Alternatively, find Proxy in Telegram settings, choose MTProto and enter server, port and secret from the link.
3. **Connect and verify.** Confirm proxy use. Wait for connection and check that messages and media load. Calls and other apps may use a different route. Keep the secret link private.

[Official guide / download](https://telegram.org/apps).

### HTTP / SOCKS5

HTTP CONNECT and SOCKS5 require a username and password; UDP is disabled. Proxy transport itself is unencrypted: use it over a VPN on untrusted networks. HTTPS keeps website content encrypted. Internal server addresses are blocked.

1. **Open the JSON.** server is the address; http_port is the HTTP port; socks5_port is the SOCKS5 port. username and password are proxy credentials, separate from your portal login.
2. **Choose where to configure it.** Wi-Fi settings can specify an HTTP proxy, but system authentication support varies. Configure proxy credentials in a compatible app where possible. This does not automatically cover every app or cellular data.
3. **Test the application.** Open an HTTPS website and check the public IP in the configured app. For SOCKS5, enable proxy-side DNS if supported. An HTTP 407 response means you should check proxy credentials.

[Official guide / download](https://curl.se/docs/manpage.html).

## Router

### General workflow and OpenWrt example

There is no universal router setup. Your firmware needs VPN client mode and support for the selected protocol. These are general steps; the link is a WireGuard example for OpenWrt.

1. **Check compatibility.** Look for VPN Client in your router manual. Standard WireGuard cannot use AmneziaWG; VLESS and Outline require a compatible additional client. If unsupported, run the VPN on your devices instead.
2. **Back up your router.** Save a router configuration backup and retain local management access. Use a separate VPN profile for the router.
3. **Import the profile.** Select the protocol in VPN Client. Import the file or enter its endpoint, keys, tunnel address and DNS. For IPsec, use the exported account settings. Keep private keys out of public services.
4. **Configure routing.** Select which devices or subnet use the VPN. Follow your firmware guide for DNS, routes and firewall; OpenWrt uses an interface and zone with LAN → VPN forwarding and masquerading. Test one device first.
5. **Check your connection.** Open a website and check your public IP and DNS. If the app says connected but websites fail, contact your administrator. A VPN indicator alone does not prove traffic is flowing.

[Official guide / download](https://openwrt.org/docs/guide-user/services/vpn/wireguard/client).

### Telegram MTProto

MTProto works only in Telegram, not as a VPN for other apps. No router configuration is needed: add the proxy in Telegram on each device.

1. **Install Telegram.** Use the official Telegram app for iOS, Android, macOS or Windows. The web client does not use this profile.
2. **Open your profile link.** Copy the tg://proxy link from your assigned profile and open it on your device. Alternatively, find Proxy in Telegram settings, choose MTProto and enter server, port and secret from the link.
3. **Connect and verify.** Confirm proxy use. Wait for connection and check that messages and media load. Calls and other apps may use a different route. Keep the secret link private.

[Official guide / download](https://telegram.org/apps).

### HTTP / SOCKS5

HTTP CONNECT and SOCKS5 require a username and password; UDP is disabled. Proxy transport itself is unencrypted: use it over a VPN on untrusted networks. HTTPS keeps website content encrypted. Internal server addresses are blocked.

1. **Open the JSON.** server is the address; http_port is the HTTP port; socks5_port is the SOCKS5 port. username and password are proxy credentials, separate from your portal login.
2. **Choose where to configure it.** Your firmware or application must support an authenticated HTTP/SOCKS5 client. WAN/DNS fields are not a substitute. Otherwise configure apps on individual devices; there is no universal router command.
3. **Test the application.** Open an HTTPS website and check the public IP in the configured app. For SOCKS5, enable proxy-side DNS if supported. An HTTP 407 response means you should check proxy credentials.

[Official guide / download](https://curl.se/docs/manpage.html).
