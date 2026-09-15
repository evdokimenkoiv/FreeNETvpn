# Implementation plan
Use the existing standard-library controller and account assignments. Render a separate pinned Xray service for HTTP/SOCKS and build official Telegram MTProxy at a fixed commit. Empty client sets use unexported random deny credentials. Recreate processes on profile revocation. Persist upstream Telegram files in the existing backup boundary and refresh daily with validated HTTPS and cached fallback. Add no public administrative endpoint.

Validate unit-level lifecycle/backup, Linux daemon authentication and external HTTPS traffic. Keep native Telegram acceptance an explicit open gate. Existing credentials and service selection survive upgrades.
