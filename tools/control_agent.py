#!/usr/bin/env python3
"""Unix-socket control service. No TCP listener or arbitrary command endpoint."""
import argparse
import hmac
import json
import os
from pathlib import Path
import socketserver

from control import Controller
from operation_lock import locked


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(35)
        try:
            raw = self.rfile.readline(65537)
            if len(raw) > 65536 or not raw.endswith(b"\n"):
                raise ValueError("Request too large")
            request = json.loads(raw)
            if not hmac.compare_digest(str(request.get("token", "")), self.server.token):
                raise ValueError("Unauthorized")
            method = request.get("method")
            if method == "snapshot":
                result = self.server.controller.snapshot()
            elif method == "telemetry":
                result = self.server.controller.telemetry.snapshot()
            elif method == "maintenance":
                result = self.server.controller.maintenance.inspect()
            elif method == "maintenance_preview":
                result = self.server.controller.maintenance.preview(request.get("data"))
            elif method == "accounts":
                data = request.get("data", {})
                if not isinstance(data, dict) or set(data) != {"action", "values"}:
                    raise ValueError("Invalid account request")
                clients = self.server.controller.snapshot()["clients"] if data["action"] == "save" else None
                result = self.server.controller.accounts.dispatch(data["action"], data["values"], clients)
            elif method == "account_export":
                data = request.get("data", {})
                if not isinstance(data, dict) or set(data) - {"username", "protocol", "name", "format"}:
                    raise ValueError("Invalid export fields")
                with locked(self.server.controller.root):
                    user = self.server.controller.accounts.get(data.get("username"))
                    clients = self.server.controller.snapshot()["clients"]
                    matching = [c for c in clients if c["protocol"] == data.get("protocol") and c["name"] == data.get("name")]
                    if not user or not user["enabled"] or len(matching) != 1 or not any(
                        all(g.get(k) == matching[0].get(k) for k in ("protocol", "name", "identity")) for g in user["grants"]
                    ):
                        raise ValueError("Profile access denied")
                    result = self.server.controller.export(**{k: v for k, v in data.items() if k != "username"})
            elif method == "submit":
                result = self.server.controller.submit(request.get("data"))
            elif method == "export":
                data = request.get("data", {})
                if set(data) - {"protocol", "name", "format"}:
                    raise ValueError("Invalid export fields")
                result = self.server.controller.export(**data)
            else:
                raise ValueError("Method not allowed")
            response = {"ok": True, "data": result}
        except Exception as error:
            response = {"ok": False, "error": str(error)[:300] if isinstance(error, ValueError) else "Сервис управления не смог выполнить запрос"}
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode() + b"\n")


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--socket", type=Path, default=Path("/run/freenetvpn/control.sock"))
    parser.add_argument("--group", type=int, default=10001)
    args = parser.parse_args()
    root = args.root.resolve()
    token = (root / "data/control.token").read_text().strip()
    if len(token) != 64:
        raise ValueError("Invalid control token; run configure/render")
    args.socket.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(args.socket.parent, 0o755)
    if args.socket.exists():
        args.socket.unlink()
    with Server(str(args.socket), Handler) as server:
        server.token = token
        server.controller = Controller(root)
        os.chmod(args.socket, 0o660)
        if os.geteuid() == 0:
            os.chown(args.socket, 0, args.group)
        server.serve_forever()


if __name__ == "__main__":
    main()
