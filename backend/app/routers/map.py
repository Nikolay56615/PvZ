from fastapi import APIRouter, Depends
import asyncpg
from ..deps import db_conn, tenant_guard

router = APIRouter(prefix="/map", tags=["map"])

@router.get("/markers")
async def markers(tenant_id: str = Depends(tenant_guard), conn: asyncpg.Connection = Depends(db_conn)):
    rows = await conn.fetch(
        """
        SELECT d.device_id::text,
               ST_Y(ST_AsText(l.location::geometry)) AS lat,
               ST_X(ST_AsText(l.location::geometry)) AS lon,
               s.status AS online,
               s.battery_level,
               s.last_seen
        FROM iot.devices d
        LEFT JOIN iot.location l ON l.device_id = d.device_id
        LEFT JOIN iot.state s    ON s.device_id = d.device_id
        WHERE d.tenant_id=$1
        """,
        tenant_id,
    )
    return [{"device_id": r["device_id"], "lat": r["lat"], "lon": r["lon"], "online": r["online"], "battery": r["battery_level"], "last_seen": r["last_seen"]} for r in rows]