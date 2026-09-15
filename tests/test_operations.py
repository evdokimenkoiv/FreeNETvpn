"""Measurement meaning, failure states, privilege and destructive-operation boundaries."""
import json
import subprocess
from types import SimpleNamespace

import pytest

import maintenance
import telemetry
from control import Controller
from test_regressions import deployment, config
from test_accounts import accounts, portal, signin


def test_network_and_connection_parsers():
    raw = 'head\n eth0: 123 1 0 0 0 0 0 0 456 0 0 0 0 0 0 0\n wg0: 999 0 0 0 0 0 0 0 999 0\n lo: 999 0 0 0 0 0 0 0 999 0'
    assert telemetry.network_bytes(raw) == [123, 456]
    with pytest.raises(ValueError): telemetry.network_bytes('lo: 0 0')
    tcp = 'header\n 0: 00000000:0438 01010101:1234 01\n 1: 00000000:0438 00000000:0000 0A\n 2: 00000000:1234 01010101:0438 01'
    assert telemetry.tcp_connections(tcp, {1080}) == 1
    assert telemetry.recent_handshakes('wg0 key 0\nwg0 key2 950\nwg0 key3 700\nwg0 key4 1100', 1000) == 1
    assert telemetry.ipsec_connections('ikev2[1]: ESTABLISHED 3 seconds\nikev2{1}: INSTALLED\nl2tp[2]: CONNECTING\nl2tp[3]: ESTABLISHED') == {'ikev2': 1, 'l2tp': 1}


@pytest.mark.parametrize('change,elapsed', [({'generation':'new'},30),({'rx_bytes':5},30),({'rx_bytes':None},30),({},120),({},0)])
def test_rates_reject_resets_gaps_and_missing(change, elapsed):
    old = {'generation':'one', 'rx_bytes':100, 'tx_bytes':200}
    current = {**old, 'rx_bytes':400, 'tx_bytes':800, **change}
    assert telemetry.rates(old,current,elapsed) == (None,None)
    assert telemetry.rates(old,{**old,'rx_bytes':400,'tx_bytes':800},30) == (10,20)


def test_history_is_bounded_private_and_restored(deployment, monkeypatch):
    now = telemetry.time.time()
    monitor = telemetry.Telemetry(deployment)
    monitor.history = [{'observed_at':now-90000,'rx_per_second':1,'tx_per_second':1}]
    def sample(t, rx): return {'observed_at':t,'rows':[{'id':'ipsec','protocols':['ikev2','l2tp'],'generation':'a','rx_bytes':rx,'tx_bytes':rx}]}
    monitor.store(sample(now,100));monitor.store(sample(now+30,400))
    result = telemetry.Telemetry(deployment).snapshot()
    assert len(result['history']) == 2
    assert result['history'][-1]['rx_per_second'] == 10  # shared service counted once
    assert len(result['sample']['rows']) == 1
    assert 'rows' not in result['history'][0]
    monitor.history = [result['history'][-1]] * 2880
    monitor.store(sample(now+60,700))
    assert len(monitor.history) == 2880
    assert len(json.dumps(monitor.snapshot())) < 2*1024*1024


def test_missing_container_is_unavailable_not_zero(deployment, monkeypatch):
    monkeypatch.setattr(telemetry,'command',lambda *a,**k:'')
    monitor=telemetry.Telemetry(deployment);monitor.sample()
    assert monitor.latest['rows']
    assert all(r['rx_bytes'] is None and r['active'] is None for r in monitor.latest['rows'])


@pytest.fixture
def service(deployment, monkeypatch):
    obj=maintenance.Maintenance(deployment)
    monkeypatch.setattr(obj,'inspect',lambda:dict(disk={'free':123},journal='1M',docker='cache'))
    return obj


def test_cleanup_preview_single_use_expiry_and_preserved_files(service, monkeypatch):
    calls=[]
    monkeypatch.setattr(maintenance,'command',lambda argv,**kw:calls.append(argv) or '')
    before=(service.root/'.env').read_bytes()
    backup=service.root/'backups/keep.tar.gz';backup.parent.mkdir(exist_ok=True);backup.write_bytes(b'keep')
    with pytest.raises(ValueError): service.cleanup('a'*64)
    with pytest.raises(ValueError): service.preview({'action':'journal','path':'/'})
    with pytest.raises(ValueError): service.preview({'action':'volumes'})
    plan=service.preview({'action':'build-cache'})
    assert calls==[]
    result=service.cleanup(plan['plan_id'])
    assert result['action']=='build-cache'
    assert calls==[['docker','builder','prune','--force','--filter','until=168h']]
    with pytest.raises(ValueError): service.cleanup(plan['plan_id'])
    plan=service.preview({'action':'journal'});service.plans[plan['plan_id']]['expires_at']=0
    with pytest.raises(ValueError): service.cleanup(plan['plan_id'])
    assert len(calls)==1 and backup.read_bytes()==b'keep' and (service.root/'.env').read_bytes()==before


def test_cleanup_failure_consumes_token_and_plan_limit(service,monkeypatch):
    def failure(*a,**kw): raise subprocess.TimeoutExpired('fixture',120)
    monkeypatch.setattr(maintenance,'command',failure)
    plan=service.preview({'action':'journal'})
    with pytest.raises(subprocess.TimeoutExpired):service.cleanup(plan['plan_id'])
    with pytest.raises(ValueError):service.cleanup(plan['plan_id'])
    for _ in range(32):service.preview({'action':'journal'})
    with pytest.raises(ValueError):service.preview({'action':'journal'})


def test_update_failure_is_not_up_to_date(service,monkeypatch):
    def failure(*a,**k):raise OSError('offline')
    monkeypatch.setattr(maintenance,'command',failure)
    monkeypatch.setattr(maintenance.urllib.request,'urlopen',failure)
    assert service.updates()['project']['status']=='unavailable'
    assert service.updated['os']['status']=='unavailable'


def test_update_check_never_installs(service,monkeypatch):
    (service.root/'data/release.json').write_text(json.dumps({'commit':'a'*40}))
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return json.dumps({'object':{'sha':'b'*40}}).encode()
    calls=[]
    monkeypatch.setattr(maintenance.urllib.request,'urlopen',lambda *a,**k:Response())
    monkeypatch.setattr(maintenance,'command',lambda argv,**k:calls.append(argv) or 'Inst one\nInst two\nConf one')
    result=service.updates()
    assert result['project']['status']=='different_revision' and result['os']['upgradable']==2
    assert calls==[['apt-get','--simulate','upgrade']]


def test_member_denied_before_privileged_backend(portal):
    headers=signin(portal)
    for path in ('telemetry','maintenance'):
        assert portal.get('/admin/api/'+path).status_code==403
    assert portal.post('/admin/api/maintenance/preview',json={'action':'journal'},headers=headers).status_code==403
    assert portal.post('/admin/api/jobs',json={'operation':'maintenance.updates'},headers=headers).status_code==403


def test_admin_preview_requires_csrf(portal,monkeypatch):
    from test_regressions import panel
    headers=signin(portal,'admin')
    assert portal.post('/admin/api/maintenance/preview',json={'action':'journal'}).status_code==403
    calls=[]
    monkeypatch.setattr(panel,'control',lambda method,data=None:calls.append((method,data)) or {})
    assert portal.post('/admin/api/maintenance/preview',json={'action':'journal'},headers=headers).status_code==200
    assert calls==[('maintenance_preview',{'action':'journal'})]


def test_controller_rejects_arbitrary_maintenance_fields(deployment):
    c=Controller(deployment,worker=False)
    for body in ({'operation':'maintenance.cleanup'}, {'operation':'maintenance.updates','protocol':'vless'},
                 {'operation':'maintenance.cleanup','plan_id':'a'*64,'command':'id'}):
        with pytest.raises(ValueError):c.validate_request(body)
