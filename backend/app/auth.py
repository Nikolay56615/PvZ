from datetime import datetime, timedelta, timezone
import jwt
from passlib.hash import bcrypt
from pydantic import BaseModel
from .config import settings

ALGO = "HS256"

class User(BaseModel):
    user_id: str
    name: str
    tenant_id: str
    permissions: str = "VIEWER"

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.verify(plain, hashed)
    except Exception:
        return False

def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.app_jwt_expires_min)
    payload = {
        "sub": user.user_id,
        "name": user.name,
        "tenant_id": user.tenant_id,
        "permissions": user.permissions,
        "exp": exp,
    }
    return jwt.encode(payload, settings.app_secret, algorithm=ALGO)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.app_secret, algorithms=[ALGO])