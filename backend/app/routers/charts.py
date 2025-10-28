from fastapi import APIRouter, Depends, Response
import asyncpg
from ..deps import db_conn, tenant_guard
from ..schemas.telemetry import RangeQuery

router = APIRouter(prefix="/charts", tags=["charts"])

@router.post("/humidity/{device_id}")
async def humidity_series(device_id: str, q: RangeQuery, tenant_id: str = Depends(tenant_guard), conn: asyncpg.Connection = Depends(db_conn)):
    owns = await conn.fetchval("SELECT 1 FROM iot.devices WHERE device_id=$1 AND tenant_id=$2", device_id, tenant_id)
    if not owns:
        return []
    rows = await conn.fetch(
        "SELECT sent_ts, humidity FROM iot.monitoring_raw WHERE device_id=$1 AND sent_ts BETWEEN $2 AND $3 ORDER BY sent_ts",
        device_id, q.since, q.until,
    )
    return [{"ts": r["sent_ts"], "humidity": r["humidity"]} for r in rows]

@router.post("/humidity/{device_id}/export.csv")
async def humidity_export(device_id: str, q: RangeQuery, tenant_id: str = Depends(tenant_guard), conn: asyncpg.Connection = Depends(db_conn)):
    rows = await conn.fetch(
        "SELECT sent_ts, humidity FROM iot.monitoring_raw WHERE device_id=$1 AND sent_ts BETWEEN $2 AND $3 ORDER BY sent_ts",
        device_id, q.since, q.until,
    )
    csv = "ts,humidity\n" + "\n".join(f"{r['sent_ts'].isoformat()},{r['humidity']}" for r in rows)
    return Response(content=csv, media_type="text/csv")