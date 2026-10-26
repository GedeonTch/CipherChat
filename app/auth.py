"""Small TP account store. No message persistence."""
import asyncio, hashlib, hmac, json, os, re, secrets, sqlite3, time
from collections import OrderedDict, deque
from fastapi import HTTPException

class Accounts:
    def __init__(self, path):
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, display TEXT NOT NULL, salt TEXT NOT NULL, digest TEXT NOT NULL)')
        self.db.commit()
        self.sessions={}
        self.attempts=OrderedDict()
        self.dummy_salt=secrets.token_hex(16)

    def user(self, token):
        item=self.sessions.get(token)
        if not item: return None
        if item[1]<time.time():
            self.sessions.pop(token,None);return None
        return item[0]

    async def body(self, request, origins):
        if request.headers.get('origin') not in origins: raise HTTPException(403,detail='origin')
        addr=request.client.host if request.client else 'unknown'
        now=time.monotonic();q=self.attempts.pop(addr,deque())
        while q and now-q[0]>60:q.popleft()
        self.attempts[addr]=q
        if len(self.attempts)>1024:self.attempts.popitem(last=False)
        if len(q)>=20:raise HTTPException(429,detail='rate')
        q.append(now)
        raw=b''
        async for part in request.stream():
            raw+=part
            if len(raw)>1024:raise HTTPException(413,detail='invalid')
        try:
            body=json.loads(raw)
            if not isinstance(body,dict):raise ValueError()
            return body
        except (ValueError,UnicodeDecodeError):raise HTTPException(400,detail='invalid')

    async def authenticate(self, body, register=False):
        if set(body)!={'nick','password'}:raise HTTPException(400,detail='invalid')
        name=body['nick'];password=body['password']
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',name):raise HTTPException(400,detail='nickname')
        if not isinstance(password,str) or not 5<=len(password)<=128 or not re.search(r'[A-Za-z]',password) or not re.search(r'[0-9]',password):raise HTTPException(400,detail='passInvalid')
        row=self.db.execute('SELECT display,salt,digest FROM accounts WHERE name=?',(name.casefold(),)).fetchone()
        salt=secrets.token_hex(16) if register else (row[1] if row else self.dummy_salt)
        digest=await asyncio.to_thread(hashlib.pbkdf2_hmac,'sha256',password.encode(),bytes.fromhex(salt),600000)
        if register:
            try:
                self.db.execute('INSERT INTO accounts VALUES (?,?,?,?)',(name.casefold(),name,salt,digest.hex()));self.db.commit()
            except sqlite3.IntegrityError:raise HTTPException(409,detail='accountExists')
        elif not row or not hmac.compare_digest(row[2],digest.hex()):raise HTTPException(401,detail='credentials')
        else:name=row[0]
        # Expired sessions are removed and the temporary session store is bounded.
        now=time.time()
        self.sessions={k:v for k,v in self.sessions.items() if v[1]>now}
        if len(self.sessions)>=2000:self.sessions.pop(next(iter(self.sessions)))
        token=secrets.token_urlsafe(32);self.sessions[token]=(name,now+8*3600)
        return name,token
