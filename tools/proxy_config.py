"""Private optional proxy configurations; never render an anonymous listener."""
import json
import os
import manage

# Explicit CIDRs avoid relying on a mutable external geodata asset.
NON_PUBLIC = ["0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
              "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16", "192.0.0.0/24",
              "192.0.2.0/24", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
              "224.0.0.0/4", "240.0.0.0/4", "::/128", "::1/128", "64:ff9b::/96",
              "100::/64", "2001:db8::/32", "2002::/16", "fc00::/7", "fe80::/10", "ff00::/8"]


def render(config, state, root):
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    os.chmod(root / "runtime", 0o700)
    enabled = config["COMPOSE_PROFILES"].split(",")
    if "proxy" in enabled and "proxy_empty_password" in state:
        accounts = [{"user": name, "pass": p["password"]} for name, p in state["clients"]["proxy"].items()]
        # A nonempty accounts array is essential: Xray HTTP otherwise allows anonymous use.
        accounts = accounts or [{"user": "_unissued", "pass": state["proxy_empty_password"]}]
        value = {"log": {"loglevel": "warning"}, "inbounds": [
            {"tag": "http", "listen": "0.0.0.0", "port": 3128, "protocol": "http", "settings": {"accounts": accounts, "allowTransparent": False}},
            {"tag": "socks", "listen": "0.0.0.0", "port": 1080, "protocol": "socks", "settings": {"auth": "password", "accounts": accounts, "udp": False}}],
            "outbounds": [{"tag": "direct", "protocol": "freedom", "settings": {"domainStrategy": "UseIP"}}, {"tag": "blocked", "protocol": "blackhole", "settings": {"response": {"type": "http"}}}],
            "routing": {"domainStrategy": "IPOnDemand", "rules": [
                {"type": "field", "domain": ["full:" + config["DOMAIN"], "full:" + config["WG_DOMAIN"]], "outboundTag": "blocked"},
                {"type": "field", "ip": NON_PUBLIC, "outboundTag": "blocked"}]}}
        # The image runs as UID 65532; the 0700 host parent protects this file,
        # while only this one file is mounted into the non-root container.
        manage.atomic_write(root / "runtime/proxy.json", json.dumps(value, indent=2) + "\n", 0o644)
    if "mtproto" in enabled and "mtproto_empty_secret" in state:
        keys = [p["secret"] for p in state["clients"]["mtproto"].values()]
        if len(keys) > 16:
            raise ValueError("MTProto supports at most 16 profiles per server")
        manage.atomic_write(root / "runtime/mtproto.json", json.dumps({"server": config["DOMAIN"], "secrets": keys or [state["mtproto_empty_secret"]]}))
