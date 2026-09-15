"""Supervise upstream MTProxy and refresh its Telegram routes daily."""
import json
import ipaddress
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import time
from urllib.request import urlopen

CACHE = Path('/data')
stopping = False


def stop(*_):
    global stopping
    stopping = True


def refresh():
    changed = False
    for name, endpoint in [('proxy-secret', 'getProxySecret'), ('proxy-multi.conf', 'getProxyConfig')]:
        target = CACHE / name
        try:
            with urlopen('https://core.telegram.org/' + endpoint, timeout=20) as response:
                data = response.read(1024 * 1024 + 1)
            if not data or len(data) > 1024 * 1024 or (name.endswith('.conf') and b'proxy_for' not in data):
                raise ValueError('Invalid Telegram upstream configuration')
            if not target.exists() or target.read_bytes() != data:
                temp = target.with_suffix('.tmp')
                temp.write_bytes(data)
                os.chmod(temp, 0o600)
                temp.replace(target)
                changed = True
        except Exception:
            if not target.exists() or not target.stat().st_size:
                raise RuntimeError('Telegram configuration unavailable and no cached copy') from None
            print('Telegram refresh unavailable; using saved upstream configuration', flush=True)
    return changed


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    config = json.loads(Path('/config/mtproto.json').read_text())
    keys = config['secrets']
    if not 1 <= len(keys) <= 16 or any(not re.fullmatch('[0-9a-f]{32}', key) for key in keys):
        raise ValueError('Invalid MTProto secret inventory')
    CACHE.mkdir(parents=True, exist_ok=True)
    refresh()
    public_ip = os.getenv('FREENET_PUBLIC_IP') or socket.gethostbyname(config['server'])
    if not ipaddress.IPv4Address(public_ip).is_global:
        raise ValueError('MTProto requires a public IPv4 endpoint')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect((public_ip, 443))
        private_ip = route.getsockname()[0]
    args = ['/usr/local/bin/mtproto-proxy', '--http-stats', '-p', '8888', '-H', '8443', '-M', '1', '--aes-pwd', str(CACHE / 'proxy-secret'), str(CACHE / 'proxy-multi.conf')]
    args += ['--nat-info', private_ip + ':' + public_ip]
    for key in keys:
        args += ['-S', key]
    # Source requires root initialization then drops daemon privileges.
    args += ['-u', 'nobody']
    child = subprocess.Popen(args)
    deadline = time.monotonic() + 86400
    try:
        while not stopping:
            if child.poll() is not None:
                raise RuntimeError('MTProxy exited; supervisor will restart the container')
            time.sleep(1)
            if time.monotonic() >= deadline:
                if refresh():
                    child.terminate()
                    child.wait(timeout=15)
                    child = subprocess.Popen(args)
                deadline = time.monotonic() + 86400
    finally:
        child.terminate()
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


if __name__ == '__main__':
    main()
