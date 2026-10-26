import base64, tempfile, json, time, sqlite3
from uuid import uuid4
from contextlib import ExitStack
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import create_app
from app.settings import Settings

ORIGIN='http://localhost:8000'
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('CHAT_DB_PATH',':memory:')
    with TestClient(create_app(Settings('ab'*16,[ORIGIN]))) as c: yield c

def auth(c,nick='Alice',password='abcd1',register=True):
    c.cookies.clear()
    r=c.post('/api/register' if register else '/api/login',json={'nick':nick,'password':password},headers={'origin':ORIGIN})
    return r

def socket(c,nick='Alice',room='1111A'):
    r=auth(c,nick)
    if r.status_code==409:r=auth(c,nick,register=False)
    assert r.status_code==200,r.text
    return c.websocket_connect('/ws',headers={'origin':ORIGIN})

def hello(w,nick='Alice',room='1111A'):
    w.send_json({'type':'join','nick':nick,'room':room});p=w.receive_json()
    if p['type']=='welcome':w.receive_json()
    return p

def packet(p,nick='Alice',room='1111A',seq=1):
    return dict(type='message',v=1,room=room,nick=nick,id=str(uuid4()),session=p['session'],seq=seq,ts='2026-10-23T12:00:00.000Z',iv=base64.b64encode(b'a'*12).decode(),ciphertext=base64.b64encode(b'x'*20).decode())

def test_health_config_headers(client):
    assert client.get('/health').json()=={'status':'ok'}
    assert client.get('/api/config').json()['mode']=='rooms'
    assert 'unsafe-inline' not in client.get('/').headers['content-security-policy']

def test_account_login_and_hash(client):
    r=auth(client);assert r.status_code==200
    assert 'HttpOnly' in r.headers['set-cookie'];assert 'SameSite=strict' in r.headers['set-cookie']
    assert client.get('/api/me').json()['nick']=='Alice'
    row=client.app.state.accounts.db.execute('SELECT salt,digest FROM accounts').fetchone()
    assert row[0]!='abcd1' and row[1]!='abcd1'
    assert auth(client,'alice',register=False).json()['nick']=='Alice'
    assert auth(client,'Alice',register=True).status_code==409
    assert auth(client,'Alice','wrong1',False).status_code==401
    assert auth(client,'Unknown','wrong1',False).status_code==401

@pytest.mark.parametrize('name,password',[('','abcd1'),('a'*25,'abcd1'),('bad name','abcd1'),('Alice','12345'),('Alice','abcde'),('Alice','ab1'),('Alice','a1'*65)])
def test_validation(client,name,password):assert auth(client,name,password).status_code==400

def test_auth_origin_and_size(client):
    assert client.post('/api/login',json={},headers={'origin':'https://evil.test'}).status_code==403
    assert client.post('/api/register',content='x'*1025,headers={'origin':ORIGIN}).status_code==413
    assert client.post('/api/register',content='no json',headers={'origin':ORIGIN}).status_code==400

def test_auth_rate(client):
    for i in range(20):assert auth(client,'','x1').status_code==400
    assert auth(client,'','x1').status_code==429

def test_ws_needs_auth_origin(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws',headers={'origin':ORIGIN}):pass
    auth(client)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/ws',headers={'origin':'https://evil.test'}):pass

def test_isolation_presence_and_quit(client):
    with socket(client) as a:
        welcome=hello(a)
        with socket(client,'Bob') as b:
            hello(b,'Bob');assert a.receive_json()['nick']=='Bob'
            with socket(client,'Other','0000E') as other:
                w=hello(other,'Other','0000E');assert w['members']==['Other']
                p=packet(welcome);a.send_json(p);assert a.receive_json()==p;assert b.receive_json()==p
                other.send_json({'type':'ping'});assert other.receive_json()['type']=='pong'
                b.send_json({'type':'quit'});assert a.receive_json()['event']=='leave'
    assert not client.app.state.members

def test_no_history_and_rejoin(client):
    with socket(client) as a:
        w=hello(a);a.send_json(packet(w));a.receive_json()
    with socket(client) as a:
        hello(a);a.send_json({'type':'ping'});assert a.receive_json()['type']=='pong'

@pytest.mark.parametrize('room',['11111','AAAAA','ab1','../1111A','#general'])
def test_room_validation(client,room):
    with socket(client) as a:assert hello(a,room=room)['code']=='roomInvalid'

def test_identity_binding(client):
    with socket(client) as a:assert hello(a,'Mallory')['code']=='authRequired'

@pytest.mark.parametrize('mutation',[{'room':'0000E'},{'seq':0},{'nick':'Bob'},{'extra':True}])
def test_packets(client,mutation):
    with socket(client) as a:
        w=hello(a);p=packet(w);p.update(mutation);a.send_json(p);assert a.receive_json()['code']=='invalid'

def test_malformed_and_size(client):
    with socket(client) as a:
        hello(a);a.send_text('not json');assert a.receive_json()['code']=='invalid'
    with socket(client) as a:
        hello(a);a.send_text('x'*8193)
        with pytest.raises(WebSocketDisconnect) as e:a.receive_json()
        assert e.value.code==1009

def test_rate_replay(client):
    with socket(client) as a:
        w=hello(a)
        for i in range(1,6):a.send_json(packet(w,seq=i));assert a.receive_json()['seq']==i
        a.send_json(packet(w,seq=6))
        with pytest.raises(WebSocketDisconnect):a.receive_json()
    with socket(client) as a:
        w=hello(a);p=packet(w);a.send_json(p);a.receive_json();a.send_json(p);assert a.receive_json()['code']=='invalid'

def test_logout_expiry(client):
    auth(client);assert client.post('/api/logout',json={},headers={'origin':ORIGIN}).status_code==200
    assert client.get('/api/me').status_code==401
    auth(client);token=client.cookies.get('cipher_session');client.app.state.accounts.sessions[token]=('Alice',0)
    assert client.get('/api/me').status_code==401

def test_salt(monkeypatch):
    monkeypatch.setenv('ALLOWED_ORIGINS',ORIGIN)
    for value in ['', 'a'*31, 'g'*32]:
        monkeypatch.setenv('CHAT_KDF_SALT',value)
        with pytest.raises(ValueError):Settings.load()
    monkeypatch.setenv('CHAT_KDF_SALT','AB'*16);assert Settings.load().salt=='ab'*16

def test_accounts_persist_without_messages(tmp_path,monkeypatch):
    path=str(tmp_path/'accounts.sqlite3');monkeypatch.setenv('CHAT_DB_PATH',path)
    with TestClient(create_app(Settings('ab'*16,[ORIGIN]))) as c:assert auth(c).status_code==200
    with TestClient(create_app(Settings('ab'*16,[ORIGIN]))) as c:
        assert auth(c,register=False).status_code==200
        assert not c.app.state.members
    db=sqlite3.connect(path);assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('accounts',)]

def test_secure_cookie_and_logout_rejects_origin(client):
    client.app.state.accounts.attempts.clear()
    # Use a second app with an HTTPS production origin.
    with TestClient(create_app(Settings('ab'*16,['https://chat.example'])),base_url='https://chat.example') as c:
        r=c.post('/api/register',json={'nick':'Secure','password':'abcd1'},headers={'origin':'https://chat.example'})
        assert r.status_code==200 and 'Secure' in r.headers['set-cookie']
        assert c.post('/api/logout',json={},headers={'origin':'https://evil.example'}).status_code==403

def test_duplicate_live_account_and_logout_cleanup(client):
    with socket(client) as a:
        hello(a)
        with client.websocket_connect('/ws',headers={'origin':ORIGIN}) as second:
            assert hello(second)['code']=='duplicate'
        assert client.post('/api/logout',json={},headers={'origin':ORIGIN}).status_code==200
        a.send_json({'type':'ping'})
        try:assert a.receive_json()['code']=='authRequired'
        except WebSocketDisconnect:pass
    assert not client.app.state.members

def test_fifty_connection_cap(client):
    auth(client)
    with ExitStack() as stack:
        for _ in range(50):stack.enter_context(client.websocket_connect('/ws',headers={'origin':ORIGIN}))
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws',headers={'origin':ORIGIN}):pass
