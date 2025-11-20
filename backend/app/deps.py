from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .auth import decode_token
import asyncpg
from .db import get_pool

bearer = HTTPBearer(auto_error=False)

def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid/expired token")

def tenant_guard(user=Depends(current_user)) -> str:
    return user.get("tenant_id")

async def db_conn() -> asyncpg.Connection:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
