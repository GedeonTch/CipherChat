import {request,uuid} from './network.js';
import {strings} from './i18n.js';import {derive,encrypt,Receiver} from './crypto.js';import {nickPattern} from './protocol.js';import {Connection} from './connection.js';
const $=s=>document.querySelector(s);let lang='fr',theme='light';try{lang=localStorage.getItem('lang')==='en'?'en':'fr';theme=localStorage.getItem('theme')==='dark'?'dark':'light';}catch{}
let status='waiting',connStatus='waiting',connection,key,session,nick,seq=0,receiver=new Receiver(),busy=false,lastFailure=0,joinError=null,roomError=null,registerMode=false,room=null,account=null;const t=k=>strings[lang][k]||strings[lang].invalid;
function clearJoinError(){joinError=null;$('#join-error').hidden=true;for(const id of ['nick','pass'])$('#'+id).removeAttribute('aria-invalid');$('#join').classList.remove('shake');}
function showJoinError(code,field){joinError=code;const el=$('#join-error');el.textContent=t(code);el.hidden=false;if(field){$('#'+field).setAttribute('aria-invalid','true');$('#'+field).focus();}const form=$('#join');form.classList.remove('shake');void form.offsetWidth;form.classList.add('shake');}
function translate(){if(roomError)$('#room-error').textContent=t(roomError);if(joinError)$('#join-error').textContent=t(joinError);document.documentElement.lang=lang;document.documentElement.dataset.theme=theme;document.querySelectorAll('[data-t]').forEach(el=>el.textContent=t(el.dataset.t));document.querySelectorAll('[data-placeholder]').forEach(el=>el.placeholder=t(el.dataset.placeholder));$('#join-button').textContent=t(registerMode?'register':'login');$('#auth-toggle').textContent=t(registerMode?'loginMode':'registerMode');$('#lang').textContent=lang==='fr'?'EN':'FR';$('#status').textContent=t(status);$('#room-status').textContent=t(status);$('#connection').textContent=t(connStatus);$('#show').textContent=t($('#pass').type==='password'?'show':'hide');strength();document.querySelectorAll('.event[data-key]').forEach(e=>e.textContent=(e.dataset.nick?e.dataset.nick+' ':'')+t(e.dataset.key));}
function setStatus(s){status=s;$('#status').textContent=t(s);$('#room-status').textContent=t(s);}function state(s){connStatus=s;$('#connection').textContent=t(s);$('#send').disabled=s!=='online';if(['duplicate','full','nickname','invalid','authRequired','roomInvalid'].includes(s)){leave(false);if(s==='authRequired'){account=null;showAccount();showJoinError(s);}else showRoomError(s);}}
function strength(){const n=[...$('#pass').value].length;$('#strength').textContent=t(n<5||!/[A-Za-z]/.test($('#pass').value)||!/[0-9]/.test($('#pass').value)?'weak':n<24?'medium':'strong');}
$('#lang').onclick=()=>{lang=lang==='fr'?'en':'fr';try{localStorage.setItem('lang',lang);}catch{}translate();};$('#theme').onclick=()=>{theme=theme==='dark'?'light':'dark';try{localStorage.setItem('theme',theme);}catch{}translate();};$('#show').onclick=()=>{$('#pass').type=$('#pass').type==='password'?'text':'password';translate();};$('#pass').oninput=()=>{strength();clearJoinError();};$('#nick').oninput=clearJoinError;$('#about-open').onclick=()=>{const d=$('#about');if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');};$('#about-close').onclick=()=>{const d=$('#about');if(typeof d.close==='function')d.close();else d.removeAttribute('open');};$('#members-toggle').onclick=()=>$('#sidebar').classList.toggle('open');
function append(el){const box=$('#messages');const bottom=box.scrollHeight-box.scrollTop-box.clientHeight<70;$('#empty')?.remove();box.append(el);while(box.children.length>500)box.firstElementChild.remove();if(bottom)box.scrollTop=box.scrollHeight;else $('#new-messages').hidden=false;}
function event(k,n=''){const el=document.createElement('p');el.className='event';el.dataset.key=k;if(['decrypt','length','invalid','offline','networkError'].includes(k))el.classList.add('validation-error');if(n)el.dataset.nick=n;el.textContent=(n?n+' ':'')+t(k);append(el);}
function members(list){$('#members').replaceChildren();for(const n of list){const li=document.createElement('li');li.textContent=n;$('#members').append(li);}$('#count').textContent=list.length;}
async function handle(p){if(!connection||!key)return;const active=connection;if(p.type==='welcome'){session=p.session;seq=0;members(p.members);return;}if(p.type==='presence'){if(p.room!==room)return;members(p.members);event(p.event==='join'?'joined':'left',p.nick);return;}if(p.type!=='message')return;if(p.room!==room)return;try{const result=await receiver.decrypt(key,p);if(active!==connection||!key)return;if(result.gap)event('gap');const article=document.createElement('article');article.className='message'+(p.session===session?' own':'');const head=document.createElement('header');head.textContent=`${p.nick} · ${new Date(p.ts).toLocaleTimeString(lang,{hour:'2-digit',minute:'2-digit'})}`;const body=document.createElement('p');body.textContent=result.text;article.append(head,body);append(article);}catch(e){if(e.message==='replay'){event('replay');return;}if(Date.now()-lastFailure>5000){event('decrypt');lastFailure=Date.now();}}}
function showAccount(){
 $('#landing').hidden=false;$('#chat').hidden=true;$('#auth-card').hidden=!!account;$('#room-panel').hidden=!account;
 if(account)$('#account-name').textContent=account;
}
function showRoomError(code){roomError=code;$('#room-error').textContent=t(code);$('#room-error').hidden=false;$('#room-code').setAttribute('aria-invalid','true');$('#room-code').focus();}
$('#auth-toggle').onclick=()=>{registerMode=!registerMode;$('#pass').autocomplete=registerMode?'new-password':'current-password';clearJoinError();translate();};
$('#join').onsubmit=async e=>{
 e.preventDefault();if(busy)return;clearJoinError();nick=$('#nick').value;
 if(!nickPattern.test(nick)){showJoinError('nickname','nick');return;}
 const password=$('#pass').value;
 if([...password].length<5||[...password].length>128||!/[A-Za-z]/.test(password)||!/[0-9]/.test(password)){showJoinError('passInvalid','pass');return;}
 busy=true;$('#join-button').disabled=true;
 try{
  await request(registerMode?'/api/register':'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nick,password})});
  const me=await request('/api/me');account=me.nick;nick=account;registerMode=false;$('#pass').autocomplete='current-password';$('#pass').value='';translate();showAccount();
 }catch(err){showJoinError(strings[lang][err.message]?err.message:'serverError');}
 finally{busy=false;$('#join-button').disabled=false;}
};
$('#room-code').oninput=()=>{roomError=null;$('#room-error').hidden=true;$('#room-code').removeAttribute('aria-invalid');};
$('#room-form').onsubmit=async e=>{
 e.preventDefault();if(busy)return;
 room=$('#room-code').value.trim().toUpperCase();
 if(!/^(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]{5,24}$/.test(room)){showRoomError('roomInvalid');return;}
 if(!globalThis.crypto||!crypto.subtle){showRoomError('unsupported');return;}
 busy=true;$('#room-join').disabled=true;$('#room-error').hidden=true;roomError=null;setStatus('preparing');
 try{
  const me=await request('/api/me');account=me.nick;nick=account;
  const c=await request('/api/config');if(c.iterations!==600000||c.v!==1||c.mode!=='rooms')throw Error('invalid');
  key=await derive(room,c.salt);receiver=new Receiver();$('#room-code').value='';$('#room-title').textContent='#'+room;
  $('#landing').hidden=true;$('#chat').hidden=false;connection=new Connection(nick,room,handle,state);connection.connect();
 }catch(err){key=null;const code=strings[lang][err.message]?err.message:'serverError';if(code==='authRequired'){account=null;showAccount();showJoinError(code);}else showRoomError(code);}
 finally{busy=false;$('#room-join').disabled=false;}
};
$('#logout').onclick=async()=>{try{await request('/api/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});leave();account=null;showAccount();}catch(err){showRoomError(strings[lang][err.message]?err.message:'serverError');}};

function leave(reset=true){connection?.stop();connection=null;key=null;session=null;room=null;receiver=new Receiver();$('#room-code').value='';$('#members').replaceChildren();$('#count').textContent='';$('#new-messages').hidden=true;$('#chat').hidden=true;showAccount();$('#messages').replaceChildren();const empty=document.createElement('p');empty.id='empty';empty.className='empty';empty.dataset.t='empty';empty.textContent=t('empty');$('#messages').append(empty);$('#text').value='';$('#sidebar').classList.remove('open');if(reset)setStatus('ready');}
$('#leave').onclick=()=>leave();$('#composer').onsubmit=async e=>{e.preventDefault();if(busy||connStatus!=='online'||!session)return;const text=$('#text').value;if(text.trim()==='/quit'){leave();return;}busy=true;$('#send').disabled=true;try{const packet=await encrypt(key,text,{nick,session,seq:++seq,id:uuid(),room,ts:new Date().toISOString()});connection.send(packet);$('#text').value='';}catch(err){event(strings[lang][err.message]?err.message:'invalid');}finally{busy=false;$('#send').disabled=connStatus!=='online';}};
$('#text').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('#composer').requestSubmit();}};$('#new-messages').onclick=()=>{const b=$('#messages');b.scrollTop=b.scrollHeight;$('#new-messages').hidden=true;};$('#messages').onscroll=()=>{const b=$('#messages');if(b.scrollHeight-b.scrollTop-b.clientHeight<70)$('#new-messages').hidden=true;};
async function health(){try{await request('/health',{},10000);if(!busy&&!connection)setStatus('ready');}catch{if(!busy&&!connection)setStatus('starting');}if(!connection)setTimeout(health,status==='ready'?30000:5000);}
translate();health();request('/api/me').then(me=>{account=me.nick;nick=account;showAccount();}).catch(e=>{if(e.message!=='authRequired')setStatus(strings[lang][e.message]?e.message:'serverError');});

window.addEventListener('pagehide',()=>{if(connection)leave();});
