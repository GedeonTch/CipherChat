import asyncio, json, re, time
from collections import deque
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .settings import Settings
from .protocol import Message

ROOT=Path(__file__).resolve().parent.parent

def create_app(settings=None):
    settings=settings or Settings.load()
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    members={}
    sockets=set()
    lock=asyncio.Lock()
    app.state.members=members

    @app.middleware('http')
    async def headers(request,call_next):
        response=await call_next(request)
        response.headers.update({'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Permissions-Policy':'camera=(), microphone=(), geolocation=()','Cache-Control':'no-store'})
        if request.url.scheme=='https': response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.get('/health')
    async def health(): return {'status':'ok'}
    @app.get('/api/config')
    async def config(): return {'v':1,'room':'#general','salt':settings.salt,'iterations':600000}
    @app.get('/')
    async def index(): return FileResponse(ROOT/'static/index.html')

    def broadcast(event):
        for entry in list(members.values()):
            try: entry['queue'].put_nowait(event)
            except asyncio.QueueFull: entry['overflow'].set()

    def presence(kind,nick):
        return {'type':'presence','event':kind,'nick':nick,'members':[e['nick'] for e in members.values()]}

    @app.websocket('/ws')
    async def websocket(ws:WebSocket):
        if ws.headers.get('origin') not in settings.origins:
            await ws.close(code=1008); return
        async with lock:
            if len(sockets)>=50:
                await ws.close(code=1008); return
            sockets.add(ws)
        await ws.accept()
        key=None; sender=None
        async def error(code):
            await ws.send_json({'type':'error','code':code})
        try:
            raw=await asyncio.wait_for(ws.receive_text(),10)
            if len(raw.encode())>8192: await ws.close(code=1009); return
            hello=json.loads(raw)
            if not isinstance(hello,dict) or set(hello)!={'type','nick'} or hello['type']!='join' or not isinstance(hello['nick'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',hello['nick']):
                await error('nickname'); return
            nick=hello['nick']; key=nick.casefold()
            async with lock:
                if key in members: key=None; await error('duplicate'); return
                if len(members)>=50: key=None; await error('full'); return
                session=str(uuid4()); queue=asyncio.Queue(maxsize=64); overflow=asyncio.Event()
                members[key]={'nick':nick,'session':session,'queue':queue,'overflow':overflow}
                await ws.send_json({'type':'welcome','session':session,'members':[e['nick'] for e in members.values()]})
                broadcast(presence('join',nick))
            async def send_loop():
                while True:
                    event=await queue.get()
                    await asyncio.wait_for(ws.send_json(event),5)
            sender=asyncio.create_task(send_loop())
            async def overflow_loop():
                await overflow.wait(); await ws.close(code=1013)
            overflow_task=asyncio.create_task(overflow_loop())
            times=deque(); controls=deque(); last_seq=0
            try:
                while True:
                    raw=await asyncio.wait_for(ws.receive_text(),65)
                    if len(raw.encode())>8192: await ws.close(code=1009); break
                    packet=json.loads(raw)
                    now=time.monotonic()
                    if isinstance(packet,dict) and packet.get('type') in ('ping','quit'):
                        while controls and now-controls[0]>=1: controls.popleft()
                        if len(controls)>=10: await ws.close(code=1008); break
                        controls.append(now)
                        if set(packet)!={'type'}: raise ValueError('control')
                        if packet['type']=='quit': break
                        queue.put_nowait({'type':'pong'}); continue
                    while times and now-times[0]>=1: times.popleft()
                    if len(times)>=5: await ws.close(code=1008); break
                    times.append(now)
                    msg=Message.model_validate(packet)
                    if msg.nick!=nick or msg.session!=session or msg.seq<=last_seq: raise ValueError('binding')
                    last_seq=msg.seq
                    broadcast(msg.model_dump())
            finally:
                overflow_task.cancel()
        except (WebSocketDisconnect,asyncio.TimeoutError): pass
        except (ValueError,TypeError,KeyError,asyncio.QueueFull):
            try: await error('invalid')
            except Exception: pass
        finally:
            sockets.discard(ws)
            if sender: sender.cancel()
            if key and key in members:
                del members[key]; broadcast(presence('leave',nick))
            try: await ws.close()
            except RuntimeError: pass
        
    app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
    return app
