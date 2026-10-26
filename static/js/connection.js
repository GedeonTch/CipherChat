export class Connection{
 constructor(nick,room,handle,state){this.room=room;this.nick=nick;this.handle=handle;this.state=state;this.stopped=false;this.attempt=0;this.lastPong=0;this.chain=Promise.resolve();}
 connect(){if(this.stopped)return;this.state('waiting');const ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);this.ws=ws;this.watchdog=setTimeout(()=>{if(!this.stopped&&this.ws===ws)ws.close();},15000);
 ws.onopen=()=>{this.lastPong=Date.now();ws.send(JSON.stringify({type:'join',nick:this.nick,room:this.room}));};
 ws.onmessage=e=>{this.chain=this.chain.then(async()=>{if(this.stopped||this.ws!==ws)return;const p=JSON.parse(e.data);if(p.type==='pong')this.lastPong=Date.now();if(p.type==='welcome'){clearTimeout(this.watchdog);this.attempt=0;this.state('online');}if(p.type==='error'){this.stopped=true;this.state(p.code);ws.close();}await this.handle(p);}).catch(()=>this.state('invalid'));};
 this.timer=setInterval(()=>{if(ws.readyState===1){if(Date.now()-this.lastPong>60000){ws.close();return;}ws.send(JSON.stringify({type:'ping'}));}},27000);
 ws.onclose=async()=>{clearTimeout(this.watchdog);clearInterval(this.timer);if(!this.stopped){try{const me=await fetch('/api/me',{credentials:'same-origin'});if(me.status===401){this.stopped=true;this.state('authRequired');return;}}catch{}if(this.stopped)return;this.state('offline');this.retry=setTimeout(()=>this.connect(),Math.min(30000,1000*2**Math.min(this.attempt++,5))+Math.random()*500);}};
 }
 send(p){if(this.ws?.readyState!==1)throw Error('offline');this.ws.send(JSON.stringify(p));}
 stop(){this.stopped=true;clearTimeout(this.watchdog);clearTimeout(this.retry);clearInterval(this.timer);if(this.ws?.readyState===1)this.ws.send(JSON.stringify({type:'quit'}));this.ws?.close();}
}
