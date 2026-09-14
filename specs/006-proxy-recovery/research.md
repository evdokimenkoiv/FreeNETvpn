# Decisions and sources
- Xray v26.3.27 is already used for VLESS. Its tagged `infra/conf/http.go` and `socks.go` use `accounts`, unlike newer online examples using `users`; use the actual pinned schema and test denial without authentication.
- https://github.com/XTLS/Xray-core/tree/v26.3.27/infra/conf
- https://github.com/TelegramMessenger/MTProxy at f36d8af769ffaeac36978d38c2c0f6d1104c2137. Official README documents multiple -S secrets, padded dd links and daily Telegram upstream configuration refresh. `net/net-tcp-rpc-ext-server.c` limits secrets to 16. Build source because the upstream prebuilt image is outdated.
- HTTP/SOCKS are TCP application proxies; they do not themselves encrypt transport or cover every device application. MTProto applies only to Telegram.
