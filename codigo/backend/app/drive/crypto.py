"""
Fernet-based encryption for Google OAuth2 tokens.
Tokens are stored encrypted in User.google_token — never in plain text.
"""
import json
from cryptography.fernet import Fernet
from app.config import get_settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_settings().FERNET_KEY.encode())
    return _fernet


def encrypt_token(token_dict: dict) -> str:
    payload = json.dumps(token_dict).encode()
    return _get_fernet().encrypt(payload).decode()


def decrypt_token(encrypted: str) -> dict:
    payload = _get_fernet().decrypt(encrypted.encode())
    return json.loads(payload)
