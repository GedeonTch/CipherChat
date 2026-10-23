import {webcrypto} from 'node:crypto';
import {test} from 'node:test';import assert from 'node:assert/strict';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
import {derive,encrypt,Receiver} from '../static/js/crypto.js';
const start=performance.now();const key=await derive('une phrase longue et forte1','ab'.repeat(16));
console.log(`PBKDF2 600000: ${(performance.now()-start).toFixed(1)} ms`);
const wrong=await derive('une autre phrase bien longue2','ab'.repeat(16));
const meta=()=>({nick:'Alice',id:crypto.randomUUID(),session:crypto.randomUUID(),seq:1,ts:new Date().toISOString()});
test('roundtrip and no plaintext',async()=>{const p=await encrypt(key,'Bonjour confidentiel',meta());assert(!JSON.stringify(p).includes('Bonjour confidentiel'));assert.equal((await new Receiver().decrypt(key,p)).text,'Bonjour confidentiel');});
test('wrong key and salt',async()=>{const p=await encrypt(key,'bonjour',meta());await assert.rejects(new Receiver().decrypt(wrong,p));const other=await derive('une phrase longue et forte1','cd'.repeat(16));await assert.rejects(new Receiver().decrypt(other,p));});
test('ciphertext and every AAD tampering',async()=>{const p=await encrypt(key,'bonjour',meta());for(const [k,v] of Object.entries({v:2,room:'#other',nick:'Bob',ts:'2026-01-01T00:00:00.000Z',session:crypto.randomUUID(),seq:2,id:crypto.randomUUID(),ciphertext:btoa('x'.repeat(23))})){await assert.rejects(new Receiver().decrypt(key,{...p,[k]:v}));}});
test('IV sample uniqueness',async()=>{const ivs=new Set();for(let i=0;i<100;i++)ivs.add((await encrypt(key,'bonjour',meta())).iv);assert.equal(ivs.size,100);});
test('replay, obsolete, gaps and failed authentication state',async()=>{const m=meta(),r=new Receiver();const p=await encrypt(key,'bonjour',m);await assert.rejects(r.decrypt(wrong,p));await r.decrypt(key,p);await assert.rejects(r.decrypt(key,p));await assert.rejects(r.decrypt(key,await encrypt(key,'ancien',{...m,id:crypto.randomUUID()})));assert((await r.decrypt(key,await encrypt(key,'suite',{...m,id:crypto.randomUUID(),seq:3}))).gap);});
test('passphrase policy: minimum five, letter and digit required',async()=>{
 for(const pass of ['ab12','abcde','12345','!!!!!','éééé1'])await assert.rejects(derive(pass,'ab'.repeat(16)));
 const shortKey=await derive('abcd1','ab'.repeat(16));
 const p=await encrypt(shortKey,'test',meta());assert.equal((await new Receiver().decrypt(shortKey,p)).text,'test');
});
