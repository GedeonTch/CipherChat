export const nickPattern=/^[A-Za-z0-9_-]{1,24}$/;
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
export function validate(p){
 const fields=['type','v','room','nick','id','session','seq','ts','iv','ciphertext'];
 if(!p||Object.keys(p).length!==fields.length||!fields.every(k=>Object.hasOwn(p,k))||p.type!=='message'||p.v!==1||p.room!=='#general'||typeof p.nick!=='string'||!nickPattern.test(p.nick)||!uuid.test(p.id)||!uuid.test(p.session)||!Number.isSafeInteger(p.seq)||p.seq<1||typeof p.ts!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(p.ts)||!Number.isFinite(Date.parse(p.ts))||new Date(p.ts).toISOString()!==p.ts)throw Error('invalid');
 for(const [k,min,max] of [['iv',12,12],['ciphertext',17,6016]]){if(typeof p[k]!=='string')throw Error('invalid');const raw=atob(p[k]);if(btoa(raw)!==p[k]||raw.length<min||raw.length>max)throw Error('invalid');}
 return p;
}
export const aad=p=>new TextEncoder().encode(JSON.stringify([p.v,p.room,p.nick,p.ts,p.session,p.seq,p.id]));
