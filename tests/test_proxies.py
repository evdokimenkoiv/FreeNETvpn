"""Proxy credential lifecycle, fail-closed defaults and recovery boundaries."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import manage
import protocols
from accounts import Accounts
from control import Controller


@pytest.fixture
def proxy_root(tmp_path, monkeypatch):
    config = dict(**manage.PORT_DEFAULTS, CONFIG_VERSION='2', DOMAIN='vpn.example.test', WG_DOMAIN='wg.example.test',
                  LE_EMAIL='ci@example.test', ADMIN_USER='admin', ADMIN_PASSWORD_HASH=manage.password_hash('testing-long-password'),
                  WG_PORT='51820', DNS1='1.1.1.1', DNS2='8.8.8.8', COMPOSE_PROFILES='proxy,mtproto',
                  VLESS_UUID='9ab3b0aa-4a2b-44b7-acd4-5a644eec3c89', VLESS_WS_PATH='/assets-proxy')
    manage.write_config(config, tmp_path)
    protocols.prepare(config, tmp_path)
    monkeypatch.setattr(manage, 'compose', lambda *a, **k: SimpleNamespace(stdout='', returncode=0))
    return tmp_path


def test_empty_proxy_is_never_anonymous(proxy_root):
    config = json.loads((proxy_root / 'runtime/proxy.json').read_text())
    for inbound in config['inbounds']:
        assert inbound['settings']['accounts'][0]['pass']
        assert inbound['settings']['accounts'][0]['user'] == '_unissued'
    assert config['inbounds'][1]['settings']['auth'] == 'password'
    assert config['inbounds'][1]['settings']['udp'] is False
    assert '127.0.0.0/8' in config['routing']['rules'][1]['ip']
    assert len(json.loads((proxy_root / 'runtime/mtproto.json').read_text())['secrets']) == 1


@pytest.mark.parametrize('protocol', ['proxy', 'mtproto'])
def test_proxy_lifecycle_identity_and_recovery(proxy_root, protocol, tmp_path):
    protocols.client('add', protocol, 'phone', proxy_root)
    controller = Controller(proxy_root, worker=False)
    first = next(c for c in controller.snapshot()['clients'] if c['name'] == 'phone')
    data = protocols.read_state(proxy_root)
    export = controller.export(protocol, 'phone')
    assert export['content']
    accounts = Accounts(proxy_root)
    accounts.dispatch('save', dict(actor='admin', username='member', display_name='Member', role='user', locale='en',
        enabled=True, password='test-long-password-123', create=True, grants=[{'protocol': protocol, 'name': 'phone'}]), [first])
    archive = manage.make_backup(proxy_root)
    target = tmp_path / 'restored'; target.mkdir()
    manage.restore(archive, target)
    assert protocols.read_state(target) == data
    assert Accounts(target).read() == accounts.read()
    with pytest.raises(ValueError):
        manage.restore(archive, proxy_root)
    protocols.client('revoke', protocol, 'phone', proxy_root)
    assert 'phone' not in protocols.read_state(proxy_root)['clients'][protocol]
    assert not list((proxy_root / 'data/exports' / protocol).glob('phone.*'))
    protocols.client('add', protocol, 'phone', proxy_root)
    second = next(c for c in controller.snapshot()['clients'] if c['name'] == 'phone')
    assert second['identity'] != first['identity']
    assert accounts.get('member')['grants'][0]['identity'] != second['identity']


def test_mtproto_limit_preserves_existing_keys(proxy_root):
    state = protocols.read_state(proxy_root)
    state['clients']['mtproto'] = {f'p{i}': {'secret': f'{i:032x}'} for i in range(16)}
    protocols.save(state, proxy_root)
    with pytest.raises(ValueError, match='16'):
        protocols.client('add', 'mtproto', 'overflow', proxy_root)
    assert protocols.read_state(proxy_root) == state


def test_failed_proxy_restart_rolls_back(proxy_root, monkeypatch):
    original = protocols.read_state(proxy_root)
    calls = []
    def compose(args, *a, **k):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError('simulated restart failure')
    monkeypatch.setattr(manage, 'compose', compose)
    with pytest.raises(RuntimeError):
        protocols.client('add', 'proxy', 'failed', proxy_root)
    assert protocols.read_state(proxy_root) == original
    assert len(calls) == 3
