# Decisions and alternatives

Decision: retain wg-easy's native database/setup and Xray configuration rendering instead of replacing their control planes. This preserves peer ownership and permits actual packet tests. Caddy terminates TLS and protects the separate WireGuard host. Rejected: a public Docker socket or sourcing .env as shell. The standard-library CLI provides deterministic validation and offline archives; root shell scripts handle Ubuntu setup. Existing stage references remain in plan.md. Public CA/DNS/reboot require independent acceptance; internal-CA CI proves only the declared controlled journeys.

## Ubuntu 26.04 qualification

Decision: extend the explicit installer OS allowlist to Ubuntu 26.04 LTS after the existing guard correctly refused it without changing the fresh VPS. Docker officially lists this release in its [Ubuntu installation requirements](https://docs.docker.com/engine/install/ubuntu/). A real x86_64 VPS installation using the official Docker apt repository is recorded in docs/vps-qualification.md. Retain Ubuntu 22.04/24.04 CI rather than implying that the VPS check is a new hosted-runner matrix entry.
