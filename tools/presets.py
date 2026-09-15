"""Versioned, allow-listed client presets; existing server identities are preserved."""
import json
from urllib.parse import urlencode, quote

CATALOG = {
    "vless": [
        {"id": "ws-tls", "name": "Универсальный", "badge": "Рекомендуем", "description": "WebSocket поверх TLS. Для повседневного подключения и большинства VLESS-клиентов.", "compatibility": "VLESS + WebSocket + TLS", "transport": "ws", "details": {"Транспорт": "WebSocket", "Шифрование": "TLS, проверка сертификата", "Порт": "443"}},
        {"id": "mobile-ws", "name": "Мобильная сеть", "badge": "Keep-alive", "description": "WebSocket/TLS с TCP keep-alive в экспортируемом Xray JSON. Подходит для проверки соединения в меняющейся сети.", "compatibility": "Xray JSON для keep-alive; URI содержит обычный WS/TLS", "transport": "ws", "keepalive": 30, "details": {"Транспорт": "WebSocket", "TCP keep-alive": "30 секунд, Xray JSON", "Порт": "443"}},
        {"id": "grpc-tls", "name": "HTTP/2 · gRPC", "badge": "Альтернатива", "description": "gRPC поверх TLS для клиентов с поддержкой HTTP/2. Удобная альтернатива WebSocket.", "compatibility": "VLESS + gRPC + TLS; HTTP/2 должен проходить через вашу сеть", "transport": "grpc", "details": {"Транспорт": "gRPC / HTTP/2", "Шифрование": "TLS, проверка сертификата", "Порт": "443"}},
    ],
    "amnezia": [
        {"id": "balanced", "name": "Сбалансированный", "badge": "Рекомендуем", "description": "Базовый профиль с умеренным количеством служебных пакетов и поддержанием NAT-сессии.", "compatibility": "AmneziaWG с поддержкой S1–S4 и H1–H4", "mtu": 1280, "keepalive": 25, "junk": {"Jc": 4, "Jmin": 40, "Jmax": 70}, "details": {"MTU": "1280", "Keep-alive": "25 секунд", "Служебные пакеты": "4 × 40–70 байт"}},
        {"id": "mobile", "name": "Мобильная сеть", "badge": "Компактные пакеты", "description": "Уменьшенный MTU и более частый keep-alive для сетей, где крупные пакеты или простой вызывают обрывы.", "compatibility": "AmneziaWG; расход батареи может быть выше", "mtu": 1200, "keepalive": 15, "junk": {"Jc": 4, "Jmin": 40, "Jmax": 70}, "details": {"MTU": "1200", "Keep-alive": "15 секунд", "Служебные пакеты": "4 × 40–70 байт"}},
        {"id": "economy", "name": "Меньше служебного трафика", "badge": "По запросу", "description": "Один служебный пакет перед handshake; постоянный keep-alive выключен. При долгом простое NAT-сессия может закрыться.", "compatibility": "AmneziaWG; для подключений, инициируемых клиентом", "mtu": 1280, "keepalive": 0, "junk": {"Jc": 1, "Jmin": 20, "Jmax": 40}, "details": {"MTU": "1280", "Keep-alive": "Выключен", "Служебные пакеты": "1 × 20–40 байт"}},
    ],
}


def get(protocol, preset=None):
    entries = CATALOG.get(protocol, [])
    if not entries:
        if preset:
            raise ValueError("This protocol has no configurable preset")
        return {}
    selected = preset or entries[0]["id"]
    for entry in entries:
        if entry["id"] == selected:
            return entry
    raise ValueError("Unknown preset for this protocol")


def grpc_name(config):
    return config["VLESS_WS_PATH"].lstrip("/") + "-grpc"


def vless_uri(config, peer, name):
    preset = get("vless", peer.get("preset"))
    query = dict(encryption="none", security="tls", sni=config["DOMAIN"], type=preset["transport"])
    if preset["transport"] == "grpc":
        query.update(serviceName=grpc_name(config), mode="gun", alpn="h2")
    else:
        query.update(host=config["DOMAIN"], path=config["VLESS_WS_PATH"])
    return f'vless://{peer["uuid"]}@{config["DOMAIN"]}:443?{urlencode(query)}#{quote(name)}'


def vless_json(config, peer):
    preset = get("vless", peer.get("preset"))
    stream = {"network": preset["transport"], "security": "tls", "tlsSettings": {"serverName": config["DOMAIN"], "allowInsecure": False}}
    if preset["transport"] == "grpc":
        stream["grpcSettings"] = {"serviceName": grpc_name(config), "multiMode": False}
        stream["tlsSettings"]["alpn"] = ["h2"]
    else:
        stream["wsSettings"] = {"path": config["VLESS_WS_PATH"], "headers": {"Host": config["DOMAIN"]}}
    if preset.get("keepalive"):
        stream["sockopt"] = {"tcpKeepAliveIdle": preset["keepalive"], "tcpKeepAliveInterval": 15}
    return {"log": {"loglevel": "warning"}, "inbounds": [{"listen": "127.0.0.1", "port": 1080, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}],
            "outbounds": [{"protocol": "vless", "settings": {"vnext": [{"address": config["DOMAIN"], "port": 443, "users": [{"id": peer["uuid"], "encryption": "none"}]}]}, "streamSettings": stream}]}


def server_inbounds(config, root):
    peers = {}
    state = root / "data/protocols.json"
    if state.exists():
        peers = json.loads(state.read_text())["clients"].get("vless", {})
    ws_clients = [{"id": config["VLESS_UUID"], "email": "legacy"}]
    grpc_clients = []
    for name, peer in peers.items():
        target = grpc_clients if get("vless", peer.get("preset"))["transport"] == "grpc" else ws_clients
        target.append({"id": peer["uuid"], "email": name})
    def inbound(port, clients, transport):
        return {"listen": "0.0.0.0", "port": port, "protocol": "vless", "settings": {"clients": clients, "decryption": "none"}, "streamSettings": transport}
    return [inbound(10000, ws_clients, {"network": "ws", "wsSettings": {"path": config["VLESS_WS_PATH"]}}),
            inbound(10001, grpc_clients, {"network": "grpc", "grpcSettings": {"serviceName": grpc_name(config)}})]
