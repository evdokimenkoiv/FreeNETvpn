#!/usr/bin/env python3
"""Linux Docker test: authenticated proxy traffic, denials and MTProxy readiness.

Uses disposable credentials and containers, never a running FreeNET installation.
MTProxy protocol/native acceptance is reported separately from this readiness check.
"""
import json
import ipaddress
import argparse
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import manage
import protocols
from mtproto_probe import probe


def run(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def wait_port(port):
    for _ in range(60):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return
        except OSError:
            time.sleep(1)
    raise AssertionError('Proxy listener did not start')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-mtproto', action='store_true', help='Verify MTProto auth/rotation via daemon counters without requiring a Telegram upstream response')
    options = parser.parse_args()
    suffix = secrets.token_hex(4)
    px, mt = 'freenet-proxy-test-' + suffix, 'freenet-mt-test-' + suffix
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        config = dict(**manage.PORT_DEFAULTS, CONFIG_VERSION='2', DOMAIN='vpn.example.test', WG_DOMAIN='wg.example.test',
            LE_EMAIL='test@example.test', ADMIN_USER='admin', ADMIN_PASSWORD_HASH=manage.password_hash(secrets.token_urlsafe(24)),
            WG_PORT='51820', DNS1='1.1.1.1', DNS2='8.8.8.8', COMPOSE_PROFILES='proxy,mtproto',
            VLESS_UUID='9ab3b0aa-4a2b-44b7-acd4-5a644eec3c89', VLESS_WS_PATH='/assets-proxy')
        manage.write_config(config, root); protocols.prepare(config, root)
        password = secrets.token_urlsafe(24)
        state = protocols.read_state(root)
        state['clients']['proxy']['tester'] = {'password': password}
        protocols.save(state, root); protocols.render(config, root)
        image = 'ghcr.io/xtls/xray-core:26.3.27'
        def start():
            run('docker', 'run', '-d', '--name', px, '-p', '127.0.0.1:23128:3128', '-p', '127.0.0.1:21080:1080',
                '-v', str(root / 'runtime/proxy.json') + ':/etc/xray/config.json:ro', image, 'run', '-config', '/etc/xray/config.json')
            wait_port(23128); wait_port(21080)
            # Docker's host listener can accept before Xray starts. Require an
            # actual HTTP authentication challenge, including after revocation.
            for _ in range(30):
                ready = run('curl', '-sS', '--max-time', '2', '--noproxy', '', '--proxy', 'http://127.0.0.1:23128',
                            '-o', '/dev/null', '-w', '%{http_code}', 'http://example.com', check=False)
                if ready.returncode == 0 and ready.stdout == '407':
                    break
                time.sleep(1)
            else:
                raise AssertionError('HTTP proxy did not become ready with mandatory authentication')
        def request(kind, credentials=True, target='https://api.ipify.org'):
            args = ['curl', '-fsS', '--max-time', '15', '--noproxy', '', '--proxy', f'{kind}://127.0.0.1:' + ('23128' if kind == 'http' else '21080')]
            if credentials:
                args += ['--proxy-user', 'tester:' + (password if credentials is True else 'wrong-password')]
            return run(*args, target, check=False)
        try:
            start()
            for kind in ['http', 'socks5h']:
                response = request(kind)
                assert response.returncode == 0, kind + ' HTTPS traffic failed: ' + response.stderr
                public_ip = str(ipaddress.IPv4Address(response.stdout.strip()))
                assert request(kind, False).returncode != 0, kind + ' allowed anonymous traffic'
                assert request(kind, 'wrong').returncode != 0, kind + ' allowed wrong password'
                for target in ['http://127.0.0.1:3128', 'http://169.254.169.254', 'http://localhost:3128']:
                    assert request(kind, target=target).returncode != 0, 'Internal destination allowed'
            run('docker', 'rm', '-f', px)
            state['clients']['proxy'].clear(); protocols.save(state, root); protocols.render(config, root); start()
            for kind in ['http', 'socks5h']:
                assert request(kind).returncode != 0, 'Revoked password accepted'
                assert request(kind, False).returncode != 0, 'Empty inventory became anonymous'
            run('docker', 'build', '-t', mt, str(ROOT / 'services/mtproto'))
            # Use the observed Docker egress, not the runner host's HTTP route
            # (which may use a different proxy/NAT address).
            def start_mt():
                run('docker', 'run', '-d', '--name', mt, '--ulimit', 'nofile=131072:131072', '-p', '127.0.0.1:28443:8443',
                    '-e', 'FREENET_PUBLIC_IP=' + public_ip, '-v', str(root / 'runtime/mtproto.json') + ':/config/mtproto.json:ro', '-v', str(root / 'data/mtproto') + ':/data', mt)
                wait_port(28443)
                for _ in range(30):
                    health = run('docker', 'inspect', '--format', '{{.State.Health.Status}}', mt).stdout.strip()
                    if health == 'healthy':
                        break
                    time.sleep(2)
                assert health == 'healthy', 'MTProxy stats endpoint unhealthy'
            def parsed_queries():
                # Upstream increments these only after decrypting and parsing a
                # valid MTProto packet, even when a Telegram target is unavailable.
                result = run('docker', 'exec', mt, 'python3', '-c', "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8888/stats',timeout=3).read().decode())").stdout
                fields = dict(line.split('\t', 1) for line in result.splitlines() if '\t' in line)
                return int(fields['tot_forwarded_queries']) + int(fields['dropped_queries'])
            def credential_check(key, accepted):
                before = parsed_queries()
                try:
                    probe('127.0.0.1', 28443, key, timeout=2)
                except OSError:
                    pass  # This assertion measures parsing, not upstream reachability.
                time.sleep(2)
                after = parsed_queries()
                assert (after > before) == accepted, 'MTProxy secret authentication boundary failed'
            start_mt()
            secret = state['mtproto_empty_secret']
            credential_check(secret, True)
            credential_check(secrets.token_hex(16), False)
            run('docker', 'rm', '-f', mt)
            state['mtproto_empty_secret'] = secrets.token_hex(16)
            protocols.save(state, root); protocols.render(config, root); start_mt()
            credential_check(secret, False)
            credential_check(state['mtproto_empty_secret'], True)
            if options.local_mtproto:
                print('NOT RUN: Telegram upstream resPQ roundtrip (--local-mtproto). Run without this flag on the deployment network.')
            else:
                for attempt in range(3):
                    try:
                        assert probe('127.0.0.1', 28443, state['mtproto_empty_secret'])
                        break
                    except OSError:
                        if attempt == 2:
                            raise
                        time.sleep(5)
                print('PASS: Telegram upstream resPQ nonce roundtrip. Native app acceptance is separate.')
            print('PASS: HTTP/SOCKS HTTPS traffic, missing/wrong/revoked credentials, private destinations and empty inventory; MTProxy build/TCP/stats, parsed authenticated packets and unknown/revoked secret rejection.')
        finally:
            if sys.exc_info()[0]:
                for container in (px, mt):
                    logs = run('docker', 'logs', container, check=False)
                    print((logs.stdout + logs.stderr).replace(password, '[redacted]'), flush=True)
            run('docker', 'rm', '-f', px, mt, check=False)


if __name__ == '__main__':
    main()
