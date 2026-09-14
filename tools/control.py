"""Restricted local control operations. Never accepts a shell command or file path."""
import base64
import contextlib
import io
import hashlib
import json
import os
import queue
import re
import secrets
import shutil
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone

import manage
import presets
import protocols
from accounts import Accounts
from operation_lock import locked

SERVICES = {"wireguard": "wg-easy", "vless": "xray", "ikev2": "ipsec", "l2tp": "ipsec", "outline": "outline", "amnezia": "amnezia", "mtproto": "mtproto", "proxy": "proxy"}
TITLES = {"client.add": "Создание клиента", "client.revoke": "Отзыв доступа", "client.preset": "Смена шаблона", "service.restart": "Перезапуск сервиса", "service.start": "Запуск сервиса", "service.stop": "Остановка сервиса", "backup.create": "Резервная копия", "wireguard.connect": "Подключение wg-easy"}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class Controller:
    def __init__(self, root, worker=True):
        self.root = root
        self.accounts = Accounts(root)
        self.lock = threading.RLock()
        self.wg_lock = threading.RLock()
        self.queue = queue.Queue(maxsize=32)
        self.path = root / "data/control/jobs.json"
        self.jobs = json.loads(self.path.read_text()) if self.path.exists() else []
        for job in self.jobs:
            if job["status"] in {"queued", "running"}:
                job.update(status="interrupted", error="Сервис управления перезапущен. Проверьте результат перед повтором.")
        if worker:
            threading.Thread(target=self.work, daemon=True).start()

    def persist(self):
        self.jobs = self.jobs[-100:]
        manage.atomic_write(self.path, json.dumps(self.jobs, ensure_ascii=False))

    def validate_request(self, request):
        if not isinstance(request, dict) or set(request) - {"operation", "protocol", "name", "preset", "request_id", "username", "password"}:
            raise ValueError("Недопустимые поля запроса")
        operation = request.get("operation")
        if operation not in TITLES:
            raise ValueError("Операция не разрешена")
        protocol = request.get("protocol")
        if operation != "backup.create":
            if protocol not in SERVICES or protocol not in manage.read_config(self.root)["COMPOSE_PROFILES"].split(","):
                raise ValueError("Протокол не включён в установке")
        if operation.startswith("client."):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", request.get("name", "")):
                raise ValueError("Имя: 1–32 латинских буквы, цифры, дефис или подчёркивание")
            if request["name"] == "legacy" and protocol == "vless":
                raise ValueError("Основной VLESS-профиль сохраняется для существующих устройств")
            presets.get(protocol, request.get("preset"))
            if operation == "client.preset" and (protocol not in presets.CATALOG or not request.get("preset")):
                raise ValueError("Выберите шаблон VLESS или AmneziaWG")
        if operation == "wireguard.connect":
            if protocol != "wireguard" or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", request.get("username", "")) or not 1 <= len(request.get("password", "")) <= 1024:
                raise ValueError("Укажите учётную запись wg-easy")

    def submit(self, request):
        self.validate_request(request)
        ident = request.get("request_id")
        if not isinstance(ident, str) or not re.fullmatch(r"[a-f0-9-]{32,36}", ident):
            raise ValueError("Требуется уникальный идентификатор запроса")
        with self.lock:
            existing = next((j for j in self.jobs if j["id"] == ident), None)
            if existing:
                return dict(existing)
            if self.queue.full():
                raise ValueError("Очередь заполнена. Дождитесь завершения операций")
            job = dict(id=ident, operation=request["operation"], title=TITLES[request["operation"]], protocol=request.get("protocol"), name=request.get("name"), status="queued", created=timestamp())
            self.jobs.append(job)
            self.persist()
            self.queue.put((ident, dict(request)))
            return dict(job)

    def work(self):
        while True:
            ident, request = self.queue.get()
            with self.lock:
                job = next(j for j in self.jobs if j["id"] == ident)
                job.update(status="running", started=timestamp())
                self.persist()
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = self.execute(request)
                with self.lock:
                    job.update(status="done", result=result or {}, finished=timestamp())
            except Exception as error:
                with self.lock:
                    # Subprocess errors may contain argv; never persist those values.
                    message = str(error) if isinstance(error, ValueError) else "Операция не завершена. Проверьте доступность сервиса и журнал на сервере."
                    job.update(status="failed", error=message[:300], finished=timestamp())
            with self.lock:
                self.persist()
            self.queue.task_done()

    def wg_api(self, action, name=None, credentials=None):
        # wg-easy login writes SQLite session state. Snapshot polling and a
        # background client job must not open concurrent native transactions.
        with self.wg_lock:
            return self._wg_api(action, name, credentials)

    def _wg_api(self, action, name=None, credentials=None):
        state = protocols.read_state(self.root)
        credentials = credentials or state.get("wireguard_credentials")
        if not credentials:
            raise ValueError("Сначала подключите учётную запись wg-easy")
        payload = dict(credentials, action=action)
        if action in {"export", "revoke"}:
            matches = [p for p in self.wg_api("list", credentials=credentials) if p["name"] == name]
            if len(matches) != 1:
                raise ValueError("Клиент WireGuard не найден или имя неоднозначно")
            payload["id"] = matches[0]["id"]
        elif action == "add":
            if any(p["name"] == name for p in self.wg_api("list", credentials=credentials)):
                raise ValueError("Клиент с таким именем уже существует")
            payload["name"] = name
        script = (self.root / "tools/wg_bridge.js").read_text()
        result = manage.compose(["exec", "-T", "wg-easy", "node", "--input-type=module", "-e", script], self.root, capture=True, input_text=json.dumps(payload))
        return json.loads(result.stdout)

    def execute(self, request):
        with locked(self.root):
            return self._execute(request)

    def _execute(self, request):
        self.validate_request(request)
        op, protocol, name = request["operation"], request.get("protocol"), request.get("name")
        if op == "client.revoke":
            self.accounts.forget_profile(protocol, name)
        if op == "backup.create":
            return {"filename": manage.make_backup(self.root).name}
        if op.startswith("service."):
            action = op.split(".")[1]
            if action == "start":
                manage.compose(["up", "-d", "--wait", SERVICES[protocol]], self.root, capture=True)
            else:
                manage.compose([action, SERVICES[protocol]], self.root, capture=True)
            return {"protocol": protocol}
        if op == "wireguard.connect":
            credentials = {"username": request["username"], "password": request["password"]}
            self.wg_api("list", credentials=credentials)
            state = protocols.read_state(self.root)
            state["wireguard_credentials"] = credentials
            protocols.save(state, self.root)
            return {"connected": True}
        action = op.split(".")[1]
        if protocol == "wireguard":
            self.wg_api(action, name)
        else:
            protocols.client(action, protocol, name, self.root, preset=request.get("preset"))
        return {"protocol": protocol, "name": name}

    def snapshot(self):
        config = manage.read_config(self.root)
        enabled = config["COMPOSE_PROFILES"].split(",")
        result = manage.compose(["ps", "--all", "--format", "json"], self.root, capture=True, check=False)
        containers = []
        if result.returncode == 0 and result.stdout.strip():
            raw = result.stdout.strip()
            containers = json.loads(raw) if raw.startswith("[") else [json.loads(line) for line in raw.splitlines()]
        by_service = {c["Service"]: c for c in containers}
        services = []
        for protocol, service in SERVICES.items():
            c = by_service.get(service, {})
            services.append(dict(id=protocol, enabled=protocol in enabled, state=c.get("State", "missing") if protocol in enabled else "disabled", health=c.get("Health", ""), shared="ikev2,l2tp" if service == "ipsec" else None))
        state = protocols.read_state(self.root)
        clients = []
        for protocol, entries in state["clients"].items():
            if protocol not in enabled:
                continue
            for name, peer in entries.items():
                identity = hashlib.sha256(str(peer.get("uuid") or peer.get("public") or peer.get("secret") or peer.get("password")).encode()).hexdigest()
                clients.append(dict(name=name, protocol=protocol, identity=identity, preset=peer.get("preset", presets.get(protocol).get("id")), address=peer.get("address")))
        if "vless" in enabled:
            clients.append(dict(name="legacy", protocol="vless", identity=hashlib.sha256(config["VLESS_UUID"].encode()).hexdigest(), preset="ws-tls", protected=True, label="Основной профиль"))
        messages = []
        for protocol in ("outline", "wireguard"):
            if protocol not in enabled:
                continue
            try:
                if protocol == "outline":
                    items = protocols.outline_api(config, self.root, "access-keys")["accessKeys"]
                else:
                    items = self.wg_api("list")
                for item in items:
                    identity = hashlib.sha256(str(item.get("publicKey") or item.get("password") or item["id"]).encode()).hexdigest()
                    clients.append(dict(name=item.get("name") or str(item["id"]), protocol=protocol, identity=identity, address=item.get("ipv4Address")))
            except Exception:
                messages.append(dict(protocol=protocol, message="Подключите wg-easy для управления клиентами" if protocol == "wireguard" and not state.get("wireguard_credentials") else "Не удалось получить список клиентов; проверьте сервис"))
        backups = [{"name": p.name, "size": p.stat().st_size, "modified": p.stat().st_mtime} for p in (self.root / "backups").glob("freenetvpn-*.tar.gz") if p.is_file() and not p.is_symlink()]
        disk = shutil.disk_usage(self.root)
        try:
            uptime = float(open("/proc/uptime").read().split()[0])
        except OSError:
            uptime = None
        with self.lock:
            jobs = [dict(j) for j in reversed(self.jobs[-40:])]
        return dict(domain=config["DOMAIN"], wg_domain=config["WG_DOMAIN"], services=services, clients=clients, messages=messages,
                    presets=presets.CATALOG, backups=sorted(backups, key=lambda b: b["name"], reverse=True), jobs=jobs,
                    server={"uptime": uptime, "load": os.getloadavg()[0] if hasattr(os, "getloadavg") else None, "disk_used": disk.used, "disk_total": disk.total},
                    wireguard_connected=bool(state.get("wireguard_credentials")), observed_at=timestamp())

    def export(self, protocol, name, format="default"):
        if protocol not in SERVICES or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", name):
            raise ValueError("Недопустимый клиент")
        config = manage.read_config(self.root)
        if protocol not in config["COMPOSE_PROFILES"].split(","):
            raise ValueError("Протокол не включён")
        if format not in {"default", "json", "bundle"}:
            raise ValueError("Неизвестный формат")
        if protocol == "wireguard":
            content = self.wg_api("export", name)["configuration"].encode()
            filename = name + ".conf"
        elif protocol == "vless" and name == "legacy":
            content = (manage.client_uri(config) + "\n").encode()
            filename = "vless-main.txt"
        else:
            state = protocols.read_state(self.root)
            if protocol != "outline" and name not in state["clients"].get(protocol, {}):
                raise ValueError("Клиент не найден")
            path = protocols.export_client(protocol, name, config, state, self.root)
            if protocol == "vless" and format == "json":
                path = path.with_suffix(".json")
            if protocol == "ikev2":
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                    for file in (path, path.with_suffix(".mobileconfig"), path.parent / "ca.pem"):
                        archive.writestr(file.name, file.read_bytes())
                return {"filename": name + "-ikev2.zip", "content": base64.b64encode(stream.getvalue()).decode(), "media_type": "application/zip"}
            filename, content = path.name, path.read_bytes()
        return {"filename": filename, "content": base64.b64encode(content).decode(), "media_type": "text/plain; charset=utf-8"}
