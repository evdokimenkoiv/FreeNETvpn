// Generate both repository guides from the same content used in the portal.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'admin/app/static/guides.js'),'utf8');
for(const locale of ['en','ru']){
  const tr=(ru,en)=>locale==='ru'?ru:en;
  const context=vm.createContext({tr});vm.runInContext(source,context);
  const devices={ios:'iOS / iPadOS',mac:'macOS',win:'Windows',android:'Android',router:tr('Роутер','Router')};
  const protocols={wireguard:'WireGuard',vless:'VLESS',ikev2:'IKEv2',l2tp:'L2TP/IPsec',outline:'Outline',amnezia:'AmneziaWG',mtproto:'Telegram MTProto',proxy:'HTTP / SOCKS5'};
  let md=`# ${tr('Инструкции для устройств','Device setup guides')}\n\n[English](devices.en.md) · [Русский](devices.ru.md)\n\n${tr('Те же инструкции доступны в кабинете: «Как подключиться». Сначала администратор должен назначить вам профиль.','The same instructions are available in the portal under Setup guides. Your administrator must assign a profile first.')}\n`;
  for(const [device,title] of Object.entries(devices)){
    md+=`\n## ${title}\n`;
    for(const [protocol,name] of Object.entries(protocols)){
      if(device==='router'&&!['wireguard','mtproto','proxy'].includes(protocol))continue;
      const detail=context.guideContent(protocol,device);
      md+=`\n### ${device==='router'&&protocol==='wireguard'?tr('Общий порядок и пример OpenWrt','General workflow and OpenWrt example'):name}\n\n`;
      if(detail.notice)md+=detail.notice+'\n\n';
      md+=detail.steps.map(([heading,body],i)=>`${i+1}. **${heading}.** ${body}`).join('\n')+'\n\n';
      md+=`[${tr('Официальная инструкция / загрузка','Official guide / download')}](${detail.link}).\n`;
    }
  }
  fs.writeFileSync(path.join(root,`docs/devices.${locale}.md`),md);
}
console.log('Generated RU/EN device guides from portal content.');
