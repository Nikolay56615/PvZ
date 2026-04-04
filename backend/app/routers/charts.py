from fastapi import APIRouter, Depends, Response
import asyncpg
import math

from ..deps import db_conn, tenant_guard
from ..schemas.telemetry import RangeQuery
from ..repositories import devices as devices_repo
from ..repositories import telemetry as telemetry_repo

router = APIRouter(prefix="/charts", tags=["charts"])


def _fake_temperature_from_humidity(humidity: float, index: int) -> float:
    base = 22.0
    humidity_effect = (50.0 - float(humidity)) * 0.08
    wave = math.sin(index / 6.0) * 1.4
    return round(base + humidity_effect + wave, 2)


@router.post("/humidity/{device_id}")
async def humidity_series(
    device_id: str,
    q: RangeQuery,
    tenant_id: str = Depends(tenant_guard),
    conn: asyncpg.Connection = Depends(db_conn),
):
    owns = await devices_repo.get_device_by_id(conn, device_id, tenant_id)
    if owns is None:
        return []

    rows = await telemetry_repo.query_humidity(
        conn,
        device_id=device_id,
        since=q.since,
        until=q.until,
    )
    return [{"ts": r["sent_ts"], "humidity": r["humidity"]} for r in rows]


@router.post("/humidity/{device_id}/export.csv")
async def humidity_export(
    device_id: str,
    q: RangeQuery,
    tenant_id: str = Depends(tenant_guard),
    conn: asyncpg.Connection = Depends(db_conn),
):
    owns = await devices_repo.get_device_by_id(conn, device_id, tenant_id)
    if owns is None:
        return []

    rows = await telemetry_repo.query_humidity_range(
        conn,
        device_id=device_id,
        since=q.since,
        until=q.until,
    )
    csv = "ts,humidity\n" + "\n".join(
        f"{r['sent_ts'].isoformat()},{r['humidity']}" for r in rows
    )
    return Response(content=csv, media_type="text/csv")


@router.post("/temperature/{device_id}")
async def temperature_series(
    device_id: str,
    q: RangeQuery,
    tenant_id: str = Depends(tenant_guard),
    conn: asyncpg.Connection = Depends(db_conn),
):
    owns = await devices_repo.get_device_by_id(conn, device_id, tenant_id)
    if owns is None:
        return []

    rows = await telemetry_repo.query_humidity(
        conn,
        device_id=device_id,
        since=q.since,
        until=q.until,
    )
    return [
        {
            "ts": r["sent_ts"],
            "temperature": _fake_temperature_from_humidity(r["humidity"], idx),
        }
        for idx, r in enumerate(rows)
        if r["humidity"] is not None
    ]


@router.post("/temperature/{device_id}/export.csv")
async def temperature_export(
    device_id: str,
    q: RangeQuery,
    tenant_id: str = Depends(tenant_guard),
    conn: asyncpg.Connection = Depends(db_conn),
):
    owns = await devices_repo.get_device_by_id(conn, device_id, tenant_id)
    if owns is None:
        return []

    rows = await telemetry_repo.query_humidity_range(
        conn,
        device_id=device_id,
        since=q.since,
        until=q.until,
    )
    csv = "ts,temperature\n" + "\n".join(
        f"{r['sent_ts'].isoformat()},{_fake_temperature_from_humidity(r['humidity'], idx)}"
        for idx, r in enumerate(rows)
        if r["humidity"] is not None
    )
    return Response(content=csv, media_type="text/csv")
