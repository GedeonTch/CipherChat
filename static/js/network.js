// iOS 15 compatible: no AbortSignal.timeout(), Object.hasOwn() or crypto.randomUUID().
export async function request(url,options={},timeout=20000){
 const controller=typeof AbortController!=='undefined'?new AbortController():null;
 const timer=controller?setTimeout(()=>controller.abort(),timeout):null;
 try{
  const response=await fetch(url,{...options,credentials:'same-origin',...(controller?{signal:controller.signal}:{})});
  let body;try{body=await response.json();}catch{throw Error('serverError');}
  if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:(response.status>=500?'serverError':'invalid'));
  return body;
 }catch(e){if(e.name==='AbortError')throw Error('timeout');if(e instanceof TypeError)throw Error('networkError');throw e;}
 finally{if(timer)clearTimeout(timer);}
}
export function uuid(){
 const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;
 const h=Array.from(b,v=>v.toString(16).padStart(2,'0')).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}
