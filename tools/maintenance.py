"""Fixed, previewed maintenance. No arbitrary command, path or URL input."""
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import time
import urllib.request

from telemetry import command

ACTIONS = {
    "journal": ["journalctl", "--vacuum-time=7d"],
    "build-cache": ["docker", "builder", "prune", "--force", "--filter", "until=168h"],
}
PROJECT_URL = "https://api.github.com/repos/evdokimenkoiv/FreeNETvpn/git/ref/heads/main"


class Maintenance:
    def __init__(self, root):
        self.root, self.lock, self.plans = root, threading.RLock(), {}
        self.cached, self.updated = None, None

    def inspect(self):
        with self.lock:
            if self.cached and time.time() - self.cached["observed_at"] < 60:
                return {**self.cached, "updates": self.updated}
            disk = shutil.disk_usage(self.root)
            result = {"observed_at": time.time(), "disk": {"used": disk.used, "free": disk.free, "total": disk.total},
                      "reboot_required": Path("/var/run/reboot-required").exists(), "journal": None, "docker": None}
            for key, argv in (("journal", ["journalctl", "--disk-usage"]),
                              ("docker", ["docker", "system", "df", "--format", "{{json .}}"] )):
                try:
                    result[key] = command(argv, timeout=8).strip()[:8000]
                except (OSError, subprocess.SubprocessError):
                    pass
            self.cached = result
            return {**result, "updates": self.updated}

    def preview(self, data):
        if not isinstance(data, dict) or set(data) != {"action"} or data["action"] not in ACTIONS:
            raise ValueError("Invalid maintenance action")
        inspection = self.inspect()
        with self.lock:
            self.plans = {k: v for k, v in self.plans.items() if v["expires_at"] > time.time()}
            if len(self.plans) >= 32:
                raise ValueError("Too many cleanup previews; wait five minutes")
            plan = {"plan_id": secrets.token_hex(32), "action": data["action"], "expires_at": time.time()+300,
                    "scope": "host_archived_journals_older_than_7_days" if data["action"] == "journal" else "host_dangling_build_cache_older_than_7_days",
                    "estimated_reclaim_bytes": None, "inspection": inspection}
            self.plans[plan["plan_id"]] = plan
            return plan

    def cleanup(self, plan_id):
        with self.lock:
            plan = self.plans.pop(plan_id, None)
        if not plan or plan["expires_at"] <= time.time():
            raise ValueError("Cleanup preview expired or already used; preview again")
        before = shutil.disk_usage(self.root).free
        # Consumed before execution: even a failed/partial cleanup must be previewed again.
        command(ACTIONS[plan["action"]], timeout=120)
        after = shutil.disk_usage(self.root).free
        self.cached = None
        return {"action": plan["action"], "scope": plan["scope"], "free_before": before, "free_after": after,
                "free_delta_bytes": after-before, "note": "Concurrent server writes may affect the free-space delta"}

    def updates(self):
        result = {"checked_at": time.time(), "project": {"status": "unavailable"}, "os": {"status": "unavailable"}}
        try:
            deployed = json.loads((self.root / "data/release.json").read_text()).get("commit")
            request = urllib.request.Request(PROJECT_URL, headers={"User-Agent": "FreeNETvpn-update-check", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(request, timeout=8) as response:
                head = json.loads(response.read(65536))["object"]["sha"]
            result["project"] = {"status": "same_revision" if deployed == head else "different_revision" if deployed else "unknown_installed",
                                 "installed": deployed, "available": head}
        except (OSError, ValueError, KeyError):
            pass
        try:
            output = command(["apt-get", "--simulate", "upgrade"], timeout=20)
            indexes = [p.stat().st_mtime for p in Path("/var/lib/apt/lists").glob("*InRelease") if p.is_file()]
            result["os"] = {"status": "cached_index", "upgradable": sum(line.startswith("Inst ") for line in output.splitlines()),
                            "index_oldest_at": min(indexes) if indexes else None}
        except (OSError, subprocess.SubprocessError):
            pass
        with self.lock:
            self.updated = result
        return result
