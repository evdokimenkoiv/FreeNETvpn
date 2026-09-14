// Browser acceptance with an explicit simulated API; real agents/VPNs are tested
// separately by integration.py. This fixture is never served by production.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const output = process.env.SCREENSHOT_DIR || path.join(root, 'runtime/ui-screenshots');
fs.mkdirSync(output, {recursive:true});
const presets = JSON.parse(execFileSync(process.env.PYTHON || 'python', ['-X','utf8','-c', 'import sys,json;sys.path.insert(0,"tools");import presets;print(json.dumps(presets.CATALOG))'], {cwd:root,encoding:'utf8'}));
const snapshot = {
  domain:'vpn.example.test',wg_domain:'wg.example.test',observed_at:new Date().toISOString(),
  services:['wireguard','vless','ikev2','l2tp','outline','amnezia','mtproto','proxy'].map(id=>({id,enabled:true,state:'running',health:'healthy'})),
  clients:[{name:'iphone-alex',protocol:'amnezia',preset:'mobile',address:'10.98.0.2'}, {name:'macbook-work',protocol:'vless',preset:'ws-tls'}, {name:'home-desktop',protocol:'wireguard',address:'10.8.0.2'}, {name:'travel-phone',protocol:'outline'}, {name:'legacy',protocol:'vless',preset:'ws-tls',protected:true,label:'Основной профиль'}],
  messages:[],presets,backups:[{name:'freenetvpn-20260911T120000Z.tar.gz',size:3543456,modified:1789128000}],jobs:[],
  server:{uptime:1087254,load:0.18,disk_used:12.4*1024**3,disk_total:80*1024**3},wireguard_connected:true
};

(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1050},deviceScaleFactor:1});
  await page.emulateMedia({reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let logged=false,offline=false,who='admin';const requests=[];
  snapshot.clients.forEach(c=>c.identity='demo-'+c.name);
  const people=[{username:'admin',display_name:'Alex Morgan',role:'admin',enabled:true,locale:'ru',is_owner:true,grants:[]},
    {username:'mira',display_name:'Mira Chen',role:'user',enabled:true,locale:'en',is_owner:false,grants:snapshot.clients.slice(0,2).map(c=>({protocol:c.protocol,name:c.name,identity:c.identity}))},
    {username:'james',display_name:'James Wilson',role:'admin',enabled:true,locale:'en',is_owner:false,grants:[]}];
  const current=()=>({...people.find(u=>u.username===who),csrf:'ui-csrf'});
  await page.route('https://vpn.example.test/**',async route=>{
    const req=route.request(),url=new URL(req.url());
    const json=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
    if(url.pathname.startsWith('/admin/assets/')){
      const name=path.basename(url.pathname);
      return route.fulfill({contentType:name.endsWith('.css')?'text/css':'text/javascript',body:fs.readFileSync(path.join(root,'admin/app/static',name))});
    }
    if(url.pathname==='/admin')return route.fulfill({contentType:'text/html',headers:{'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'"},body:fs.readFileSync(path.join(root,'admin/app/static/index.html'),'utf8').replace('{{WG_DOMAIN}}',snapshot.wg_domain)});
    if(url.pathname.endsWith('/login')){logged=true;who=req.postDataJSON().username;return json(current());}
    if(!logged)return json({detail:'Войдите в кабинет'},401);
    if(url.pathname.endsWith('/session'))return json(current());
    if(url.pathname.endsWith('/users')){
      if(req.method()==='GET')return json({users:people,audit:[]});
      assert.equal(req.headers()['x-csrf-token'],'ui-csrf');
      const body=req.postDataJSON();requests.push(body);const row={...body,is_owner:false,grants:body.grants.map(g=>({...g,identity:'demo-'+g.name}))};delete row.password;
      const i=people.findIndex(u=>u.username===body.username);if(i<0)people.push(row);else people[i]=row;return json({ok:true});
    }
    if(url.pathname.includes('/users/')&&req.method()==='DELETE'){people.splice(people.findIndex(u=>u.username===url.pathname.split('/').at(-1)),1);return json({ok:true});}
    if(url.pathname.endsWith('/logout')){logged=false;return json({ok:true});}
    if(url.pathname.endsWith('/overview'))return offline?json({detail:'Сервис управления недоступен'},503):json(who==='mira'?{domain:snapshot.domain,clients:snapshot.clients.slice(0,2),observed_at:snapshot.observed_at}:snapshot);
    if(url.pathname.endsWith('/export'))return json({filename:url.searchParams.get('name')+'.txt',content:Buffer.from('vless://test-fixture@vpn.example.test:443?security=tls').toString('base64'),media_type:'text/plain'});
    if(url.pathname.endsWith('/qr'))return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="white"/><path d="M10 10h30v30H10z M60 10h30v30H60z M10 60h30v30H10z M60 60h10v10H60z" fill="black"/></svg>'});
    if(url.pathname.endsWith('/jobs')){
      assert.equal(req.headers()['x-csrf-token'],'ui-csrf');
      const body=req.postDataJSON();requests.push(body);
      const job={id:body.request_id,status:'done',title:'Изменение доступа',created:new Date().toISOString(),...body};snapshot.jobs.unshift(job);
      if(body.operation==='client.add')snapshot.clients.push({name:body.name,protocol:body.protocol,preset:body.preset});
      if(body.operation==='client.revoke')snapshot.clients=snapshot.clients.filter(c=>c.name!==body.name||c.protocol!==body.protocol);
      if(body.operation==='client.preset')snapshot.clients.find(c=>c.name===body.name&&c.protocol===body.protocol).preset=body.preset;
      return json(job,202);
    }
    return json({detail:'Unexpected endpoint'},404);
  });
  try{
    await page.goto('https://vpn.example.test/admin');
    await page.locator('#login-screen').waitFor({state:'visible'});
    await page.locator('.login-language').selectOption('ru');
    await page.screenshot({path:path.join(output,'freenet-login.png')});
    await page.locator('[name=password]').fill('ui-test-password');
    await page.locator('#login-form button').click();
    await page.locator('.service-card').first().waitFor();
    assert.equal(await page.locator('.service-card').count(),8);
    await page.screenshot({path:path.join(output,'freenet-dashboard.png'),fullPage:true});
    await page.locator('nav [data-page=users]').click();
    await page.locator('.person-card').first().waitFor();
    await page.waitForFunction(()=>document.querySelector('nav [data-page=users]').getAttribute('aria-current')==='page');
    await page.screenshot({path:path.join(output,'freenet-users.png'),fullPage:true});
    await page.locator('[data-action=new-user]').click();
    await page.locator('#user-form [name=display_name]').fill('Taylor Reed');
    await page.locator('#user-form [name=username]').fill('taylor');
    await page.locator('#user-form [name=password]').fill('Fixture-password-2026!');
    await page.locator('#user-form [name=grant]').first().check();
    await page.locator('#user-form [type=submit]').click();
    await page.locator('[data-action=edit-user][data-name=taylor]').waitFor();
    assert.equal(requests.at(-1).role,'user');assert.equal(requests.at(-1).grants.length,1);
    await page.locator('[data-action=edit-user][data-name=taylor]').click();
    await page.locator('#user-role').selectOption('admin');
    assert.ok(await page.locator('#grant-section').isHidden());
    await page.locator('#user-form [type=submit]').click();
    await page.locator('[data-action=edit-user][data-name=taylor]').waitFor();
    assert.equal(requests.at(-1).role,'admin');
    await page.locator('[data-action=edit-user][data-name=taylor]').click();
    await page.locator('[data-action=delete-user]').click();await page.locator('#confirm-operation').click();
    await page.locator('[data-action=edit-user][data-name=taylor]').waitFor({state:'hidden'});
    await page.locator('nav [data-page=presets]').click();
    await page.locator('.preset-card').first().waitFor();
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await page.locator('.preset-card').count(),6);
    await page.screenshot({path:path.join(output,'freenet-presets.png'),fullPage:true});
    await page.locator('[data-action=create][data-protocol=vless][data-preset=grpc-tls]').click();
    assert.equal(await page.locator('input[name=preset]:checked').inputValue(),'grpc-tls');
    await page.locator('#client-form [name=name]').fill('test-mobile');
    await page.locator('#client-form button[type=submit]').click();
    await page.locator('#download-profile').waitFor();
    assert.equal(requests.at(-1).preset,'grpc-tls');
    const download=page.waitForEvent('download');await page.locator('#download-profile').click();assert.equal((await download).suggestedFilename(),'test-mobile.txt');
    await page.locator('#close-dialog').click();
    await page.locator('nav [data-page=clients]').click();
    await page.locator('#client-search').fill('test-mobile');
    assert.equal(await page.locator('tbody tr').count(),1);
    await page.locator('[data-action=preset][data-name=test-mobile]').click();
    await page.locator('input[name=preset][value=mobile-ws]').check();
    await page.locator('#client-form button[type=submit]').click();
    await page.locator('#download-profile').waitFor();
    assert.equal(requests.at(-1).operation,'client.preset');
    await page.locator('#close-dialog').click();
    await page.locator('[data-action=revoke][data-name=test-mobile]').click();
    await page.locator('#confirm-operation').click();
    await page.locator('.empty').waitFor();
    assert.equal(requests.at(-1).operation,'client.revoke');
    await page.locator('#client-search').fill('');
    // Text from upstream names must never become executable markup.
    snapshot.clients.push({name:'<img src=x onerror=alert(1)>',protocol:'wireguard'});
    await page.locator('#refresh').click();
    await page.getByText('<img src=x onerror=alert(1)>',{exact:true}).first().waitFor();
    assert.equal(await page.locator('tbody img').count(),0);
    snapshot.clients.pop();
    offline=true;await page.locator('#refresh').click();await page.locator('#error-banner').waitFor({state:'visible'});
    offline=false;await page.locator('#refresh').click();await page.locator('#error-banner').waitFor({state:'hidden'});
    await page.setViewportSize({width:390,height:844});
    await page.locator('#menu-toggle').click();
    await page.locator('nav [data-page=overview]').click();
    await page.locator('.service-card').first().waitFor();
    await page.waitForFunction(()=>document.querySelector('#sidebar').getBoundingClientRect().right<=0);
    await page.locator('.toast').first().waitFor({state:'hidden'});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,'freenet-mobile.png'),fullPage:true});
    await page.locator('#menu-toggle').click();await page.locator('#logout').click();
    await page.locator('#login-screen').waitFor({state:'visible'});
    await page.setViewportSize({width:1440,height:1050});
    await page.locator('#login-form [name=username]').fill('mira');
    await page.locator('#login-form [name=password]').fill('Fixture-password-2026!');
    await page.locator('#login-form [type=submit]').click();
    await page.locator('.connection-card').first().waitFor();
    assert.equal(await page.locator('nav [data-page=users]').count(),0);
    assert.equal(await page.locator('[data-action=create]').count(),0);
    await page.locator('#app .language-select').selectOption('en');
    assert.equal(await page.locator('#connection-label').innerText(),'Connected');
    assert.match(await page.locator('#updated-at').innerText(),/^Updated /);
    await page.screenshot({path:path.join(output,'freenet-member-en.png'),fullPage:true});
    await page.locator('nav [data-page=guides]').click();
    for(const device of ['ios','mac','win','android','router']){
      await page.locator('[data-device='+device+']').click();
      assert.ok(await page.locator('.guide-steps li').count()>=4);
    }
    await page.locator('[data-device=ios]').click();
    await page.screenshot({path:path.join(output,'freenet-guides-en.png'),fullPage:true});
    // A stale administrative deep-link cannot reveal administrative components.
    await page.evaluate(()=>location.hash='users');
    await page.locator('.connection-card').first().waitFor();
    assert.equal(await page.locator('.person-card').count(),0);
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,'freenet-member-mobile.png'),fullPage:true});
    await page.locator('#app .language-select').selectOption('ru');
    await page.setViewportSize({width:1440,height:1050});
    await page.screenshot({path:path.join(output,'freenet-member-ru.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: desktop/mobile login, navigation, six presets, create/export/download/change/revoke, escaping and offline recovery');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
