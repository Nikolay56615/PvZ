from fastapi import APIRouter, Depends, Query
from typing import List
import asyncpg
from ..deps import db_conn, tenant_guard
from ..schemas.devices import DeviceOut, CommandIn
from ..repositories import devices as repo
from ..mqtt_runtime import publish_command

router = APIRouter(prefix="/devices", tags=["devices"])

@router.get("/", response_model=List[DeviceOut])
async def list_devices(tenant_id: str | None = Query(None, alias='tenant_id'), tenant_from_token: str = Depends(tenant_guard), conn: asyncpg.Connection = Depends(db_conn)):
    effective_tenant = tenant_id or tenant_from_token
    rows = await repo.list_devices(conn, effective_tenant)
    return [
        DeviceOut(
            device_id=r["device_id"], external_id=r["external_id"], model=r["model"], status=r["status"],
            rssi=r["rssi"], snr=r["snr"], battery=r["battery_level"], online=r["online"],
            lat=r["lat"], lon=r["lon"], location_updated_at=r["location_updated_at"],
        )
        for r in rows
    ]

@router.post("/{device_id}/command")
async def send_command(device_id: str, payload: CommandIn, tenant_id: str = Depends(tenant_guard)):
    cmd_id = await publish_command(
        tenant_id=tenant_id,
        device_id=device_id,
        type_=payload.type,
        params=payload.params,
        retain=payload.retain,
    )
    return {"command_id": cmd_id}
