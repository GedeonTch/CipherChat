import {aad,validate} from './protocol.js';
const encoder=new TextEncoder();
const b64=b=>btoa(String.fromCharCode(...b));
const bytes=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
export async function derive(pass,salt){
 if(typeof pass!=='string'||[...pass].length<5||!/[A-Za-z]/.test(pass)||!/[0-9]/.test(pass)||!/^[a-fA-F0-9]{32}$/.test(salt))throw Error('invalid');
 const material=await crypto.subtle.importKey('raw',encoder.encode(pass),'PBKDF2',false,['deriveKey']);
 return crypto.subtle.deriveKey({name:'PBKDF2',salt:Uint8Array.from(salt.match(/../g),x=>parseInt(x,16)),iterations:600000,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
}
export async function encrypt(key,text,meta){
 if(!text.trim()||[...text].length>2000)throw Error('length');
 const iv=crypto.getRandomValues(new Uint8Array(12));
 const p={type:'message',v:1,room:'#general',...meta,iv:b64(iv)};
 p.ciphertext=b64(new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:aad(p),tagLength:128},key,encoder.encode(text))));
 validate(p);if(encoder.encode(JSON.stringify(p)).length>8192)throw Error('length');return p;
}
export class Receiver{
 constructor(){this.ids=new Set();this.sessions=new Map();}
 async decrypt(key,p){
 validate(p);
 if(this.ids.has(p.id)||p.seq<=(this.sessions.get(p.session)||0))throw Error('replay');
 const text=new TextDecoder('utf-8',{fatal:true}).decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:bytes(p.iv),additionalData:aad(p),tagLength:128},key,bytes(p.ciphertext)));
 if(!text.trim()||[...text].length>2000)throw Error('length');
 const previous=this.sessions.get(p.session);const gap=previous!==undefined&&p.seq!==previous+1;
 this.ids.add(p.id);this.sessions.delete(p.session);this.sessions.set(p.session,p.seq);
 if(this.ids.size>4096)this.ids.delete(this.ids.values().next().value);
 if(this.sessions.size>512)this.sessions.delete(this.sessions.keys().next().value);
 return {text,gap};
 }
}
