import base64, json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import Settings

@pytest.fixture
def client():
    with TestClient(create_app(Settings('ab'*16,['http://localhost:8000']))) as c: yield c

def join(c,nick='Alice'):
    ws=c.websocket_connect('/ws',headers={'origin':'http://localhost:8000'})
    return ws

def packet(welcome,nick='Alice',seq=1):
    return dict(type='message',v=1,room='#general',nick=nick,id=str(uuid4()),session=welcome['session'],seq=seq,ts='2026-10-23T12:00:00.000Z',iv=base64.b64encode(b'0'*12).decode(),ciphertext=base64.b64encode(b'x'*20).decode())

def hello(w,nick='Alice'):
    w.send_json({'type':'join','nick':nick}); a=w.receive_json();
    if a['type']=='welcome': w.receive_json()
    return a

def test_health(client):
    r=client.get('/health'); assert r.json()=={'status':'ok'}; assert 'unsafe-inline' not in r.headers['content-security-policy']

def test_origin(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws',headers={'origin':'https://evil.test'}): pass

def test_presence_broadcast_quit(client):
    with join(client) as a:
        wa=hello(a)
        with join(client) as b:
            hello(b,'Bob'); assert a.receive_json()['event']=='join'
            p=packet(wa); a.send_json(p)
            assert a.receive_json()==p; assert b.receive_json()==p
            b.send_json({'type':'ping'}); assert b.receive_json()=={'type':'pong'}
            b.send_json({'type':'quit'})
            assert a.receive_json()['event']=='leave'
    assert not client.app.state.members

@pytest.mark.parametrize('nick',['','a'*25,'<script>','avec espace'])
def test_nick(client,nick):
    with join(client) as w: assert hello(w,nick)['code']=='nickname'

def test_duplicate(client):
    with join(client) as a:
        hello(a)
        with join(client) as b: assert hello(b,'alice')['code']=='duplicate'

@pytest.mark.parametrize('bad',[{}, {'type':'message'}, {'type':'ping','extra':1}])
def test_invalid(client,bad):
    with join(client) as w:
        hello(w); w.send_json(bad); assert w.receive_json()['code']=='invalid'

def test_size(client):
    from starlette.websockets import WebSocketDisconnect
    with join(client) as w:
        hello(w); w.send_text('x'*8193)
        with pytest.raises(WebSocketDisconnect) as e: w.receive_json()
        assert e.value.code==1009

def test_rate(client):
    from starlette.websockets import WebSocketDisconnect
    with join(client) as w:
        a=hello(w)
        for i in range(1,6): w.send_json(packet(a,seq=i)); assert w.receive_json()['seq']==i
        w.send_json(packet(a,seq=6))
        with pytest.raises(WebSocketDisconnect): w.receive_json()

def test_salt(monkeypatch):
    monkeypatch.setenv('ALLOWED_ORIGINS','http://localhost:8000')
    for salt in ('','ab','g'*32,' '+ 'a'*32):
        monkeypatch.setenv('CHAT_KDF_SALT',salt)
        with pytest.raises(ValueError): Settings.load()
    monkeypatch.setenv('CHAT_KDF_SALT','AB'*16)
    assert Settings.load().salt=='ab'*16
    assert Settings.load()==Settings.load()

def test_no_history(client):
    with join(client) as a:
        wa=hello(a); a.send_json(packet(wa)); a.receive_json()
        with join(client) as b:
            hello(b,'Bob'); b.send_json({'type':'ping'}); assert b.receive_json()['type']=='pong'

def test_capacity(client):
    from contextlib import ExitStack
    with ExitStack() as stack:
        for i in range(50):
            w=stack.enter_context(join(client));assert hello(w,f'user{i}')['type']=='welcome'
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with join(client): pass
    assert not client.app.state.members

def test_binding_and_obsolete(client):
    for field,value in [('nick','Mallory'),('session',str(uuid4())),('seq',0),('extra',True)]:
        with join(client) as w:
            a=hello(w);p=packet(a);p[field]=value;w.send_json(p);assert w.receive_json()['code']=='invalid'
    with join(client) as w:
        a=hello(w);p=packet(a);w.send_json(p);w.receive_json();w.send_json(p);assert w.receive_json()['code']=='invalid'

def test_missing_origin(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws'): pass

def test_config_public_stable(client):
    a=client.get('/api/config').json();assert a['salt']=='ab'*16;assert a['iterations']==600000
    with TestClient(create_app(Settings('ab'*16,['http://localhost:8000']))) as second:
        assert second.get('/api/config').json()==a
    assert client.get('/').status_code==200
    assert client.get('/static/js/crypto.js').status_code==200

@pytest.mark.parametrize('origin',['*','https://example.com/path','https://example.com.evil/path','http://example.com',''])
def test_origins_config(monkeypatch,origin):
    monkeypatch.setenv('CHAT_KDF_SALT','ab'*16);monkeypatch.setenv('ALLOWED_ORIGINS',origin)
    with pytest.raises(ValueError): Settings.load()
