# FreeNETvpn principles

Version: 1.0.0 | Ratified: 2026-09-11

1. A supported deployment must have a reproducible configuration, health checks and a documented acceptance test. A successful image build alone is not evidence of a working VPN.
2. Installation and upgrades must preserve existing credentials, keys and client data. Destructive replacement requires an explicit operation and a recoverable backup.
3. Administrative endpoints require authentication. No public Docker socket or general-purpose remote command API. Never silently change SSH authentication, port or access.
4. Configuration is data: never source user-provided .env files as shell code. Validate domains, ports, service selections and generated protocol configurations before starting services.
5. CI failures must fail the workflow. Unit, configuration and Linux integration checks cover the user journeys declared in each feature specification.
6. Secrets and runtime state stay outside Git. The documentation distinguishes automated evidence from external network acceptance that has not been performed.
