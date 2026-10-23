import os, re
from dataclasses import dataclass

@dataclass
class Settings:
    salt: str
    origins: list[str]

    @classmethod
    def load(cls):
        salt = os.getenv('CHAT_KDF_SALT', '')
        if not re.fullmatch(r'[0-9a-fA-F]{32}', salt):
            raise ValueError('CHAT_KDF_SALT must contain exactly 32 hexadecimal characters')
        origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
        from urllib.parse import urlsplit
        for origin in origins:
            u = urlsplit(origin)
            if u.scheme not in ('http', 'https') or not u.netloc or u.path or u.query or u.fragment or '*' in origin or u.username:
                raise ValueError('ALLOWED_ORIGINS must contain explicit origins without paths')
            if u.scheme != 'https' and u.hostname not in ('localhost','127.0.0.1','[::1]','::1'):
                raise ValueError('Non-local origins must use HTTPS')
        return cls(salt.lower(), origins)
