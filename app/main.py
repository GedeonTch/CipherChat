import asyncio, json, re, time, os, sqlite3
from collections import deque
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .settings import Settings
from .protocol import Message
from .auth import Accounts

ROOT=Path(__file__).resolve().parent.parent

def create_app(settings=None):
    settings=settings or Settings.load()
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    accounts=Accounts(os.getenv("CHAT_DB_PATH",str(ROOT/"accounts.sqlite3")))
    app.state.accounts=accounts
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

    @app.exception_handler(sqlite3.Error)
    async def storage_error(request, exc):
        return JSONResponse({'detail':'storage'},status_code=503)

    async def sign_in(request, register=False):
        body=await accounts.body(request,settings.origins)
        name,token=await accounts.authenticate(body,register)
        old=request.cookies.get('cipher_session')
        accounts.sessions.pop(old,None)
        response=JSONResponse({'nick':name})
        response.set_cookie('cipher_session',token,httponly=True,secure=request.headers.get('origin','').startswith('https://'),samesite='strict',max_age=28800,path='/')
        return response

    @app.post('/api/register')
    async def register(request:Request): return await sign_in(request,True)
    @app.post('/api/login')
    async def login(request:Request): return await sign_in(request)
    @app.get('/api/me')
    async def me(request:Request):
        name=accounts.user(request.cookies.get('cipher_session'))
        if not name: raise HTTPException(401,detail='authRequired')
        return {'nick':name}
    @app.post('/api/logout')
    async def logout(request:Request):
        await accounts.body(request,settings.origins)
        accounts.sessions.pop(request.cookies.get('cipher_session'),None)
        response=JSONResponse({'ok':True});response.delete_cookie('cipher_session',path='/')
        return response

    @app.get('/health')
    async def health(): return {'status':'ok'}
    @app.get('/api/config')
    async def config(): return {'v':1,'mode':'rooms','salt':settings.salt,'iterations':600000}
    @app.get('/')
    async def index(): return FileResponse(ROOT/'static/index.html')

    def broadcast(event,room):
        for entry in list(members.values()):
            if entry['room']!=room:continue
            try: entry['queue'].put_nowait(event)
            except asyncio.QueueFull: entry['overflow'].set()

    def presence(kind,nick,room):
        return {'type':'presence','event':kind,'nick':nick,'room':room,'members':[e['nick'] for e in members.values() if e['room']==room]}

    @app.websocket('/ws')
    async def websocket(ws:WebSocket):
        if ws.headers.get('origin') not in settings.origins:
            await ws.close(code=1008); return
        token=ws.cookies.get('cipher_session')
        account=accounts.user(token)
        if not account:
            await ws.close(code=1008);return
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
            if not isinstance(hello,dict) or set(hello)!={'type','nick','room'} or hello['type']!='join' or not isinstance(hello['nick'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',hello['nick']):
                await error('nickname'); return
            if hello['nick']!=account:
                await error('authRequired');return
            room=hello['room']
            if not isinstance(room,str) or not re.fullmatch(r'(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]{5,24}',room):
                await error('roomInvalid');return
            nick=account; key=nick.casefold()
            async with lock:
                if key in members: key=None; await error('duplicate'); return
                if len(members)>=50: key=None; await error('full'); return
                session=str(uuid4()); queue=asyncio.Queue(maxsize=64); overflow=asyncio.Event()
                members[key]={'nick':nick,'session':session,'queue':queue,'overflow':overflow,'room':room}
                await ws.send_json({'type':'welcome','session':session,'members':[e['nick'] for e in members.values() if e['room']==room],'room':room})
                broadcast(presence('join',nick,room),room)
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
                    if not accounts.user(token):
                        queue.put_nowait({'type':'error','code':'authRequired'});await asyncio.sleep(0);break
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
                    if msg.room!=room or msg.nick!=nick or msg.session!=session or msg.seq<=last_seq: raise ValueError('binding')
                    last_seq=msg.seq
                    broadcast(msg.model_dump(),room)
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
                del members[key]; broadcast(presence('leave',nick,room),room)
            try: await ws.close()
            except RuntimeError: pass
        
    app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
    return app
