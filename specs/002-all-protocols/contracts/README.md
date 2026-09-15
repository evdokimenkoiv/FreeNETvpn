# Protocol client contract

tools/protocols.py client operations are add/list/export/revoke/preset. An enabled protocol and a valid unique name are required for creation; invalid names, disabled protocols, unknown presets and conflicting ports fail explicitly. Existing v2 config receives defaults in memory without rewriting its secrets. IKEv2 exports certificate/EAP connection material; L2TP exports IPsec/PPP settings; AmneziaWG exports matching server obfuscation and client keys; Outline exports an ss:// key from its loopback TLS API. WireGuard retains its native UI and API. Feature 003 exposes these capabilities through its allowlisted agent; cabinet IKEv2 download is a ZIP bundle and QR is unavailable for IKEv2/L2TP.

Tests: tests/test_protocols.py for lifecycle, migration and secret preservation; tests/integration_extra.py for real clients and HTTP. Importing an export in a native mobile application remains an external acceptance step.
