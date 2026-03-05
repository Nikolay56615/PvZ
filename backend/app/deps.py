from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .auth import decode_token
import asyncpg
from .db import get_pool
from .services.config import settings
import re

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid/expired token")


async def db_conn() -> asyncpg.Connection:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def tenant_guard(user=Depends(current_user), tenant_id: str | None = Query(None, alias='tenant_id'), conn: asyncpg.Connection = Depends(db_conn)) -> str:
    if tenant_id:
        if not re.fullmatch(r"[0-9a-fA-F\-]{32,36}", tenant_id):
            raise HTTPException(status_code=403, detail="Invalid tenant id")

        if user.get('permissions') in {"ADMIN", "OWNER"}:
            return tenant_id

        token_tid = user.get('tenant_id')
        if isinstance(token_tid, str) and token_tid == tenant_id:
            return tenant_id

        try:
            row = await conn.fetchrow("SELECT tenant_owner FROM iot.tenant WHERE tenant_id = $1", tenant_id)
        except Exception:
            raise HTTPException(status_code=403, detail="Tenant lookup failed")

        if not row:
            raise HTTPException(status_code=403, detail="Tenant not found")

        tenant_owner = row.get('tenant_owner')
        if tenant_owner and tenant_owner == user.get('name'):
            return tenant_id

        raise HTTPException(status_code=403, detail="Not allowed for tenant")

    tid = user.get("tenant_id")
    if isinstance(tid, str) and re.fullmatch(r"[0-9a-fA-F\-]{32,36}", tid):
        return tid
    raise HTTPException(status_code=403, detail="Tenant not found or not set in token")

