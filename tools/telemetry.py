"""Bounded aggregate measurements. Never exports peer keys or remote addresses."""
import json
from pathlib import Path
import subprocess
import threading
import time

import manage
from operation_lock import locked

GROUPS = {"wg-easy": ["wireguard"], "xray": ["vless"], "ipsec": ["ikev2", "l2tp"],
          "outline": ["outline"], "amnezia": ["amnezia"], "mtproto": ["mtproto"], "proxy": ["proxy"]}


def command(argv, timeout=5):
    return subprocess.run(argv, capture_output=True, text=True, check=True, timeout=timeout).stdout


def network_bytes(text):
    pairs = []
    for line in text.splitlines():
        if ":" not in line:
            continue
        interface, values = line.split(":", 1)
        if interface.strip().startswith("eth"):
            fields = values.split()
            pairs.append((int(fields[0]), int(fields[8])))
    if not pairs:
        raise ValueError("No bridge interface")
    return [sum(p[i] for p in pairs) for i in (0, 1)]


def tcp_connections(text, ports):
    return sum(1 for line in text.splitlines()[1:] if len(fields := line.split()) >= 4
               and fields[3] == "01" and int(fields[1].rsplit(":", 1)[1], 16) in ports)


def recent_handshakes(text, now):
    return sum(1 for line in text.splitlines() if line.strip() and 0 <= now - int(line.split()[-1]) <= 180)


def ipsec_connections(text):
    # Count IKE SAs, not child SAs, retransmits or configured connection entries.
    return {p: sum(1 for line in text.splitlines() if line.strip().startswith(p + "[") and "ESTABLISHED" in line)
            for p in ("ikev2", "l2tp")}


def rates(previous, current, elapsed):
    if not previous or previous.get("generation") != current.get("generation") or not 0 < elapsed <= 90:
        return None, None
    values = [current.get(k) for k in ("rx_bytes", "tx_bytes")] + [previous.get(k) for k in ("rx_bytes", "tx_bytes")]
    if any(v is None for v in values) or any(values[i] < values[i+2] for i in (0, 1)):
        return None, None
    return tuple(round((values[i]-values[i+2])/elapsed, 2) for i in (0, 1))


class Telemetry:
    def __init__(self, root):
        self.root, self.lock = root, threading.RLock()
        self.latest = None
        self.path = root / "data/control/telemetry.json"
        try:
            saved = json.loads(self.path.read_text())
            self.history, self.latest = saved["history"][-2880:], saved.get("sample")
        except (OSError, ValueError, KeyError, TypeError):
            self.history = []
        self.history = [s for s in self.history if isinstance(s, dict) and s.get("observed_at", 0) >= time.time()-86400]

    def snapshot(self):
        with self.lock:
            return {"sample": self.latest, "history": list(self.history),
                    "interval_seconds": 30, "retention_hours": 24, "now": time.time()}

    def run(self):
        while True:
            started = time.monotonic()
            try:
                with locked(self.root):
                    self.sample()
            except Exception:
                # A whole-collector failure still creates a gap, never a fresh-looking old sample.
                try:
                    self.store({"observed_at": time.time(), "rows": [], "error": "collector_unavailable"})
                except OSError:
                    pass  # Full disk must not kill the sampler or control agent.
            time.sleep(max(1, 30-(time.monotonic()-started)))

    def store(self, sample):
        with self.lock:
            previous = self.latest
            by_id = {r["id"]: r for r in previous["rows"]} if previous else {}
            for row in sample["rows"]:
                row["rx_per_second"], row["tx_per_second"] = rates(by_id.get(row["id"]), row,
                    sample["observed_at"] - previous["observed_at"] if previous else 0)
            valid = bool(sample["rows"]) and all(r["rx_per_second"] is not None for r in sample["rows"])
            point = {"observed_at": sample["observed_at"],
                     "rx_per_second": round(sum(r["rx_per_second"] for r in sample["rows"]), 2) if valid else None,
                     "tx_per_second": round(sum(r["tx_per_second"] for r in sample["rows"]), 2) if valid else None}
            self.history = [s for s in self.history if s["observed_at"] >= sample["observed_at"]-86400][-2879:] + [point]
            self.latest = sample
            manage.atomic_write(self.path, json.dumps({"history": self.history, "sample": sample}, separators=(",", ":")))

    def sample(self):
        now, config = time.time(), manage.read_config(self.root)
        enabled = config["COMPOSE_PROFILES"].split(",")
        ids = command(["docker", "ps", "--filter", "label=com.docker.compose.project=freenetvpn", "--format", "{{.ID}}"] ).split()
        containers = json.loads(command(["docker", "inspect", *ids])) if ids else []
        found = {c["Config"]["Labels"].get("com.docker.compose.service"): c for c in containers}
        rows = []
        for service, protocols in GROUPS.items():
            selected = [p for p in protocols if p in enabled]
            if not selected:
                continue
            row = {"id": service, "protocols": selected, "rx_bytes": None, "tx_bytes": None,
                   "active": None, "active_kind": "unavailable", "generation": None, "status": "unavailable"}
            rows.append(row)
            c = found.get(service)
            if not c or not c["State"]["Running"] or c["HostConfig"]["NetworkMode"] in {"host", "none"}:
                continue
            pid = int(c["State"]["Pid"])
            if pid <= 0:
                continue
            proc = Path(f"/proc/{pid}/net")
            row["generation"] = c["Id"][:12] + ":" + c["State"]["StartedAt"]
            try:
                row["rx_bytes"], row["tx_bytes"] = network_bytes((proc / "dev").read_text())
                row["status"] = "ok"
            except (OSError, ValueError, IndexError):
                pass
            try:
                if service in {"wg-easy", "amnezia"}:
                    binary = "wg" if service == "wg-easy" else "awg"
                    row["active"] = recent_handshakes(command(["docker", "exec", c["Id"], binary, "show", "all", "latest-handshakes"]), now)
                    row["active_kind"] = "handshake_180s"
                elif service == "ipsec":
                    row["active"] = ipsec_connections(command(["docker", "exec", c["Id"], "ipsec", "statusall"]))
                    row["active_kind"] = "ike_sa"
                else:
                    if service == "xray":
                        ports = {int(i["port"]) for i in json.loads((self.root / "runtime/xray.json").read_text())["inbounds"]}
                    else:
                        keys = {"outline": ["OUTLINE_PORT"], "mtproto": ["MTPROTO_PORT"], "proxy": ["HTTP_PROXY_PORT", "SOCKS_PROXY_PORT"]}[service]
                        ports = {int(config[k]) for k in keys}
                    row["active"] = sum(tcp_connections((proc / table).read_text(), ports) for table in ("tcp", "tcp6"))
                    row["active_kind"] = "tcp_inbound"
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                pass
        self.store({"observed_at": now, "rows": rows})
