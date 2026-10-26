import base64, re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Message(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    type: str
    v: int
    room: str
    nick: str
    id: str
    session: str
    seq: int = Field(ge=1, le=9007199254740991)
    ts: str
    iv: str
    ciphertext: str

    @field_validator('type','v')
    @classmethod
    def constants(cls, value, info):
        if value != {'type':'message','room':'#general','v':1}[info.field_name]:
            raise ValueError('protocol')
        return value

    @field_validator('room')
    @classmethod
    def room_code(cls,value):
        if not re.fullmatch(r'(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]{5,24}',value):raise ValueError('room')
        return value

    @field_validator('nick')
    @classmethod
    def nickname(cls, value):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',value): raise ValueError('nickname')
        return value

    @field_validator('id','session')
    @classmethod
    def identifier(cls,value):
        if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',value): raise ValueError('uuid')
        return value

    @field_validator('ts')
    @classmethod
    def timestamp(cls,value):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z',value): raise ValueError('timestamp')
        datetime.strptime(value,'%Y-%m-%dT%H:%M:%S.%fZ')
        return value

    @field_validator('iv','ciphertext')
    @classmethod
    def binary(cls,value,info):
        b=base64.b64decode(value,validate=True)
        if base64.b64encode(b).decode()!=value: raise ValueError('base64')
        if info.field_name=='iv' and len(b)!=12: raise ValueError('iv')
        if info.field_name=='ciphertext' and not 17<=len(b)<=6016: raise ValueError('ciphertext')
        return value
