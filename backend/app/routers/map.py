from fastapi import APIRouter, Depends
import asyncpg
from ..deps import db_conn, tenant_guard
from ..repositories import devices as repo
router = APIRouter(prefix="/map", tags=["map"])

@router.get("/markers")
async def markers(tenant_id: str = Depends(tenant_guard), conn: asyncpg.Connection = Depends(db_conn)):
    rows = await repo.get_markers(conn, tenant_id)
    return [{"device_id": r["device_id"], "lat": r["lat"], "lon": r["lon"], "online": r["online"], "battery": r["battery_level"], "last_seen": r["last_seen"]} for r in rows]