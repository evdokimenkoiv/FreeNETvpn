"""Privilege boundaries, durable credentials and identity-bound assignments."""
import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from test_regressions import panel, deployment, config, PASSWORD
from accounts import Accounts

PROFILES = [dict(protocol='vless', name='alice-phone', identity='first-key'), dict(protocol='vless', name='bob-phone', identity='second-key')]


@pytest.fixture
def accounts(deployment):
    return Accounts(deployment)


def create(accounts, name, role='user'):
    accounts.dispatch('save', dict(actor='admin', username=name, display_name=name, role=role, enabled=True,
        locale='en', password=PASSWORD, create=True, grants=[dict(protocol='vless', name='alice-phone')]), PROFILES)


def test_account_storage_revisions_and_owner_protection(accounts):
    create(accounts, 'alice')
    user = accounts.authenticate('alice', PASSWORD)
    assert user['role'] == 'user' and 'password_hash' not in user
    assert PASSWORD not in accounts.path.read_text()
    assert Accounts(accounts.root).authenticate('alice', PASSWORD) == user
    for action in ['save', 'delete', 'password']:
        with pytest.raises(ValueError, match='protected'):
            accounts.dispatch(action, dict(actor='admin', **({'username':'admin'} if action != 'password' else {})))
    accounts.dispatch('delete', dict(actor='admin', username='alice'))
    create(accounts, 'alice')
    assert accounts.get('alice')['revision'] != user['revision']
    assert all('password' not in json.dumps(row) for row in accounts.read()['audit'])


def test_assignments_and_nonadmin_mutations(accounts):
    create(accounts, 'alice')
    for action in ['list', 'save', 'delete']:
        with pytest.raises(ValueError, match='Administrator'):
            accounts.dispatch(action, dict(actor='alice'))
    with pytest.raises(ValueError, match='does not exist'):
        accounts.dispatch('save', dict(actor='admin',username='bob', display_name='Bob',role='user',enabled=True,
            locale='en',password=PASSWORD,create=True,grants=[dict(protocol='vless',name='missing')]),PROFILES)
    accounts.forget_profile('vless','alice-phone')
    assert accounts.get('alice')['grants'] == []


@pytest.fixture
def portal(accounts, deployment, monkeypatch):
    create(accounts, 'alice');create(accounts,'second-admin','admin')
    monkeypatch.setattr(panel,'CONFIG',deployment/'runtime/admin.json')
    def dispatch(method,data=None):
        if method=='accounts':return accounts.dispatch(data['action'],data['values'],PROFILES)
        if method=='snapshot':return dict(domain='vpn.example.test',wg_domain='private.example',clients=PROFILES,services=['private'],backups=['secret.tar.gz'],jobs=[{'secret':'hidden'}],server={'private':'hidden'},observed_at='2026-09-14T00:00:00Z')
        if method=='account_export':
            user=accounts.get(data['username'])
            assert any(panel.permitted(user,p) for p in PROFILES if p['name']==data['name'])
            return {'content':base64.b64encode(b'vless://fixture').decode(),'filename':'fixture.txt','media_type':'text/plain'}
        raise AssertionError('Privileged backend called: '+method)
    monkeypatch.setattr(panel,'control',dispatch)
    with TestClient(panel.app,base_url='https://vpn.example.test') as client:yield client


def signin(client,name='alice'):
    r=client.post('/admin/api/login',json=dict(username=name,password=PASSWORD),headers={'Origin':'https://vpn.example.test'})
    assert r.status_code==200
    return {'Origin':'https://vpn.example.test','X-CSRF-Token':r.json()['csrf']}


def test_user_isolation_all_sensitive_routes(portal):
    headers=signin(portal)
    assert portal.get('/admin/api/session').json()['role']=='user'
    data=portal.get('/admin/api/overview').json()
    assert set(data)=={'domain','clients','observed_at'}
    assert [c['name'] for c in data['clients']]==['alice-phone']
    assert 'identity' not in data['clients'][0]
    assert portal.get('/auth').status_code==401
    for path in ['/admin/status','/admin/backups','/admin/backup','/admin/backups/freenetvpn-test.tar.gz','/admin/api/users']:
        assert portal.get(path).status_code==403,path
    assert portal.post('/admin/api/jobs',json={'operation':'backup.create'},headers=headers).status_code==403
    assert portal.post('/admin/api/users',json={},headers=headers).status_code==403
    assert portal.delete('/admin/api/users/admin',headers=headers).status_code==403
    for endpoint in ['export','qr']:
        assert portal.get(f'/admin/api/{endpoint}?protocol=vless&name=bob-phone').status_code==403
        assert portal.get(f'/admin/api/{endpoint}?protocol=vless&name=alice-phone').status_code==200
    portal.cookies.clear()
    assert portal.get('/auth',auth=('alice',PASSWORD)).status_code==403
    assert portal.get('/admin/api/export?protocol=vless&name=bob-phone',auth=('alice',PASSWORD)).status_code==403


def test_live_disable_reset_delete_and_role_change_invalidate_sessions(portal,accounts):
    for change in [dict(enabled=False),dict(password=PASSWORD+'new'),dict(role='admin')]:
        if accounts.get('alice'):
            accounts.dispatch('delete',dict(actor='admin',username='alice'))
        create(accounts,'alice');signin(portal)
        accounts.dispatch('save',dict(actor='admin',username='alice',display_name='Alice',role='user',enabled=True,
            locale='en',grants=[],create=False,**{k:v for k,v in change.items() if k=='password'}) | {k:v for k,v in change.items() if k!='password'},PROFILES)
        assert portal.get('/admin/api/session').status_code==401
    accounts.dispatch('delete',dict(actor='admin',username='alice'));create(accounts,'alice');signin(portal)
    accounts.dispatch('delete',dict(actor='admin',username='alice'));create(accounts,'alice')
    assert portal.get('/admin/api/session').status_code==401


def test_admin_management_csrf_and_password_change(portal,accounts):
    headers=signin(portal,'second-admin')
    assert portal.get('/admin/api/users').status_code==200
    assert portal.post('/admin/api/users',json={}).status_code==403
    assert portal.post('/admin/api/users',json={'actor':'admin'},headers=headers).status_code==422
    headers=signin(portal)
    result=portal.post('/admin/api/password',json={'current_password':PASSWORD,'password':PASSWORD+'changed'},headers=headers)
    assert result.status_code==200
    assert accounts.authenticate('alice',PASSWORD) is None
    assert accounts.authenticate('alice',PASSWORD+'changed')
    assert portal.get('/admin/api/session').status_code==401


def test_recreated_profile_does_not_inherit_assignment(accounts):
    create(accounts,'alice')
    assert panel.permitted(accounts.get('alice'),PROFILES[0])
    assert not panel.permitted(accounts.get('alice'),dict(PROFILES[0],identity='new-key'))


def test_account_backup_restore_roundtrip(accounts,monkeypatch,tmp_path):
    import manage
    from types import SimpleNamespace
    create(accounts,'alice')
    monkeypatch.setattr(manage,'compose',lambda *a,**k:SimpleNamespace(stdout=''))
    archive=manage.make_backup(accounts.root)
    target=tmp_path/'restored';target.mkdir()
    manage.restore(archive,target)
    restored=Accounts(target)
    assert restored.read()==accounts.read()
    assert restored.authenticate('alice',PASSWORD)==accounts.authenticate('alice',PASSWORD)


@pytest.mark.parametrize('case',['allowed','wrong_profile','recreated','disabled','invalid_token'])
def test_actual_agent_export_boundary(accounts,case):
    import socketserver
    if not hasattr(socketserver,'ThreadingUnixStreamServer'):
        pytest.skip('Unix agent is Linux-only')
    import io
    from types import SimpleNamespace
    from control import Controller
    from control_agent import Handler
    create(accounts,'alice')
    controller=Controller(accounts.root,worker=False)
    profiles=[dict(p) for p in PROFILES]
    if case=='recreated':profiles[0]['identity']='replacement-key'
    if case=='disabled':
        s=accounts.read();s['users']['alice']['enabled']=False;accounts.persist(s,'admin','save','alice')
    controller.snapshot=lambda:dict(clients=profiles)
    calls=[]
    controller.export=lambda **values:calls.append(values) or {'content':'allowed'}
    request={'token':'wrong' if case=='invalid_token' else 'a'*64,'method':'account_export','data':{'username':'alice','protocol':'vless','name':'bob-phone' if case=='wrong_profile' else 'alice-phone'}}
    handler=Handler.__new__(Handler);handler.connection=SimpleNamespace(settimeout=lambda _:None)
    handler.server=SimpleNamespace(token='a'*64,controller=controller)
    handler.rfile=io.BytesIO(json.dumps(request).encode()+b'\n');handler.wfile=io.BytesIO()
    handler.handle();response=json.loads(handler.wfile.getvalue())
    assert response['ok']==(case=='allowed')
    assert bool(calls)==(case=='allowed')
