# Implementation plan

Extend the existing FastAPI/Caddy deployment without a frontend build dependency. Serve static HTML/CSS/JavaScript and local QR SVG. The browser uses session authentication and a JSON API; it never sees the control-agent token.

Run `tools/control_agent.py` through systemd. A group-restricted Unix socket authenticates each bounded JSON request, then dispatches a fixed read operation or a serialized background job. The agent reuses validated management/protocol functions and a fixed wg-easy native API adapter; credentials enter that adapter on stdin. State and exports stay in the existing backup boundary.

Keep preset definitions in `tools/presets.py`. Store a preset ID beside each client; derive Xray JSON/URI and AWG exports from validated catalog entries. Render a second gRPC Xray inbound and Caddy h2c route while retaining the legacy WebSocket user. Restore prior VLESS state if validation/start fails.

Verification: Python authentication/CSRF/allowlist/secret-redaction and preset lifecycle tests; Chromium desktop/mobile tests using an explicitly simulated API; real systemd agent and native WireGuard operations through HTTPS; real VLESS WS/mobile/gRPC and AWG balanced/mobile/economy packet tests on both Linux baselines. Retain prior IKEv2/L2TP/Outline tests.

Constitution check: preserved credentials, no general command endpoint or public Docker socket, configuration validated as data, reproducible dependencies and explicit evidence limitations. The allowlisted local agent extends the earlier read-only panel without weakening these project principles.

## Technical context and project structure

Python 3.12 for development/CI; stdlib management and Spec Kit helper scripts; FastAPI admin with pinned dependencies; Docker Compose and systemd on Ubuntu 22.04/24.04/26.04 x86_64 for runtime. Ubuntu 26.04 host qualification is recorded separately in docs/vps-qualification.md; the packet CI matrix remains 22.04/24.04. Windows supports development checks, not the VPN server runtime. Sources live in tools/, admin/, services/ and scripts/; tests/ contains regression, browser and Linux traffic suites. No runtime dependency on Specify CLI.

## Design artifacts

- research.md records decisions and rejected alternatives.
- data-model.md defines ownership, secret boundaries and invariants.
- contracts/ defines this feature's external interface; 003 owns the cabinet/agent contract.
- quickstart.md gives the repeatable validation path.

## Phases and constitution check

Setup establishes artifact/dependency inputs; foundation validates ownership/security; each prioritized story is implemented and independently verified; final cross-cutting checks preserve historical evidence and external acceptance. tasks.md lists exact source/test paths and dependencies. All six constitution principles apply: reproducible checks; preserve existing secrets/data; authenticated administration without arbitrary commands; validate configuration as data; failing CI; secret-free Git and explicit external limitations. No exception is requested.
