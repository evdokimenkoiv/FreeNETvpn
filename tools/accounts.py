"""Private account registry owned by the local agent; no web filesystem writes."""
import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone

import manage
from operation_lock import locked

PROTOCOLS = {'wireguard', 'vless', 'ikev2', 'l2tp', 'outline', 'amnezia'}


def verify(password, encoded):
    try:
        algorithm, rounds, salt, digest = encoded.split(':')
        if algorithm != 'pbkdf2_sha256' or not 100000 <= int(rounds) <= 1000000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


def password_hash(password):
    if not isinstance(password, str) or not 16 <= len(password) <= 1024:
        raise ValueError('Password must contain 16–1024 characters')
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()
    return f'pbkdf2_sha256:600000:{salt}:{digest}'


class Accounts:
    def __init__(self, root):
        self.root = root
        self.path = root / 'data/control/accounts.json'

    def read(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {'version': 1, 'users': {}, 'audit': []}

    def owner(self):
        c = manage.read_config(self.root)
        return dict(username=c['ADMIN_USER'], display_name=c['ADMIN_USER'], role='admin', enabled=True,
                    locale='ru', grants=[], revision='owner', is_owner=True)

    def get(self, username):
        owner = self.owner()
        if username == owner['username']:
            return owner
        account = self.read()['users'].get(username)
        return {k: v for k, v in account.items() if k != 'password_hash'} if account else None

    def authenticate(self, username, password):
        c = manage.read_config(self.root)
        account = self.get(username)
        encoded = (self.read()['users'].get(username) or {}).get('password_hash', c['ADMIN_PASSWORD_HASH'])
        if username == c['ADMIN_USER']:
            encoded = c['ADMIN_PASSWORD_HASH']
        correct = verify(password, encoded)
        return account if correct and account and account['enabled'] else None

    def persist(self, state, actor, action, target):
        state['audit'] = (state['audit'] + [dict(actor=actor, action=action, target=target,
                           created=datetime.now(timezone.utc).isoformat())])[-200:]
        manage.atomic_write(self.path, json.dumps(state, ensure_ascii=False), 0o600)

    def dispatch(self, action, data, clients=None):
        if not isinstance(data, dict):
            raise ValueError('Invalid account request')
        allowed = {
            'authenticate': {'username', 'password'}, 'get': {'username'}, 'list': {'actor'},
            'save': {'actor', 'username', 'display_name', 'role', 'enabled', 'locale', 'grants', 'password', 'create'},
            'delete': {'actor', 'username'}, 'password': {'actor', 'current_password', 'password'},
        }
        if action not in allowed or set(data) - allowed[action]:
            raise ValueError('Invalid account fields')
        with locked(self.root):
            if action == 'get':
                return self.get(data.get('username'))
            if action == 'authenticate':
                if not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
                    raise ValueError('Invalid credentials')
                return self.authenticate(data['username'], data['password'])
            actor = self.get(data.get('actor'))
            if not actor or not actor['enabled'] or (action != 'password' and actor['role'] != 'admin'):
                raise ValueError('Administrator access required')
            state = self.read()
            if action == 'list':
                return dict(users=[self.owner()] + [self.get(n) for n in sorted(state['users'])], audit=state['audit'][::-1])
            username = data.get('username', actor['username'])
            if username == self.owner()['username']:
                raise ValueError('The installation owner is protected; manage its password in server configuration')
            if action == 'password':
                if not self.authenticate(actor['username'], data.get('current_password', '')):
                    raise ValueError('Current password is incorrect')
                user = state['users'][actor['username']]
                user.update(password_hash=password_hash(data.get('password')), revision=secrets.token_hex(16))
            elif action == 'delete':
                if username == actor['username']:
                    raise ValueError('You cannot delete your own account')
                if username not in state['users']:
                    raise ValueError('Account not found')
                del state['users'][username]
            else:
                if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', username):
                    raise ValueError('Username: 1–64 letters, digits, dash or underscore')
                old = state['users'].get(username)
                if not isinstance(data.get('create'), bool) or data['create'] == bool(old):
                    raise ValueError('Account already exists' if old else 'Account not found')
                if not old and len(state['users']) >= 1000:
                    raise ValueError('Account limit reached')
                role, enabled, locale = data.get('role'), data.get('enabled'), data.get('locale')
                display = data.get('display_name', username)
                if role not in {'admin', 'user'} or not isinstance(enabled, bool) or locale not in {'ru', 'en'}:
                    raise ValueError('Invalid role, status or language')
                if not isinstance(display, str) or not 1 <= len(display.strip()) <= 80:
                    raise ValueError('Display name must contain 1–80 characters')
                if username == actor['username'] and (not enabled or role != 'admin'):
                    raise ValueError('You cannot disable or demote your own account')
                grants = data.get('grants', [])
                if not isinstance(grants, list) or len(grants) > 500:
                    raise ValueError('Invalid profile assignments')
                available = {(c['protocol'], c['name']): c.get('identity') for c in (clients or [])}
                normalized = set()
                for grant in grants:
                    if not isinstance(grant, dict) or set(grant) != {'protocol', 'name'}:
                        raise ValueError('Invalid profile assignment')
                    pair = (grant['protocol'], grant['name'])
                    if not all(isinstance(v, str) for v in pair) or pair not in available or not available[pair]:
                        raise ValueError('Assigned profile does not exist')
                    normalized.add(pair)
                encoded = password_hash(data['password']) if data.get('password') else (old or {}).get('password_hash')
                if not encoded:
                    raise ValueError('A new account requires a password')
                state['users'][username] = dict(username=username, display_name=display.strip(), role=role,
                    enabled=enabled, locale=locale, grants=[dict(protocol=p, name=n, identity=available[(p, n)]) for p, n in sorted(normalized)],
                    password_hash=encoded, revision=secrets.token_hex(16), is_owner=False)
            self.persist(state, actor['username'], action, username)
            return {'ok': True}

    def forget_profile(self, protocol, name):
        """A revoked name must not inherit an old assignment when it is reused."""
        with locked(self.root):
            state = self.read()
            changed = False
            for user in state['users'].values():
                grants = [g for g in user['grants'] if (g['protocol'], g['name']) != (protocol, name)]
                if grants != user['grants']:
                    user.update(grants=grants, revision=secrets.token_hex(16))
                    changed = True
            if changed:
                self.persist(state, 'system', 'profile.revoked', protocol + '/' + name)
