// Fixed wg-easy API adapter. Request data arrives on stdin, never in argv.
let input = '';
for await (const chunk of process.stdin) input += chunk;
const request = JSON.parse(input);
if (!['list', 'add', 'export', 'revoke'].includes(request.action)) throw Error('Unsupported action');
if (['export', 'revoke'].includes(request.action) && !/^\d+$/.test(String(request.id))) throw Error('Invalid client id');
const base = 'http://127.0.0.1:51821';
const login = await fetch(base + '/api/auth/password', {signal: AbortSignal.timeout(15000), method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: request.username, password: request.password, remember: false})});
if (!login.ok) throw Error('wg-easy authentication failed');
const cookie = login.headers.getSetCookie().map(c => c.split(';')[0]).join('; ');
let path = '/api/client', method = 'GET', body;
if (request.action === 'add') { method = 'POST'; body = JSON.stringify({name: request.name, expiresAt: null}); }
if (request.action === 'export') path += '/' + request.id + '/configuration';
if (request.action === 'revoke') { path += '/' + request.id; method = 'DELETE'; }
const response = await fetch(base + path, {signal: AbortSignal.timeout(15000), method, body, headers: {'Content-Type': 'application/json', Cookie: cookie}});
if (!response.ok) throw Error('wg-easy operation failed: ' + response.status);
const text = await response.text();
process.stdout.write(JSON.stringify(request.action === 'export' ? {configuration: text} : (text ? JSON.parse(text) : {})));
