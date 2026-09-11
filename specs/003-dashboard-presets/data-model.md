# Data model and invariants

Session: random cookie token held in web-process memory, 8-hour expiry, CSRF token; maximum 100 sessions. Login limit: 12 attempts per minute per request IP. Agent token never reaches the browser.

Job: request_id matches [a-f0-9-]{32,36}; operation is allowlisted. Persisted metadata is id/operation/title/protocol/name/status/created plus started/finished/result/error as applicable, never request passwords. Lifecycle: queued → running → done|failed; agent restart maps queued/running to interrupted. Pending queue capacity 32; history maximum 100; duplicate IDs return the stored job while retained in history (not an indefinite idempotency guarantee).

Client/Preset: named VLESS UUID and AWG private key survive preset changes. Legacy VLESS user is protected. VLESS catalog: ws-tls/mobile-ws/grpc-tls; AWG catalog: balanced/mobile/economy. AWG changes MTU/keepalive/J fields while server S/H values and keys remain unchanged. Export is {filename, media_type, content}, content is base64; overview omits secrets. See tools/control.py, tools/presets.py and contracts/.
