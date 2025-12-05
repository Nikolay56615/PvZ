import asyncpg
from typing import Sequence

async def list_devices(conn: asyncpg.Connection, tenant_id: str) -> Sequence[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT d.device_id::text, d.model, d.status,
               s.battery_level, s.status AS online, s.rssi, s.snr, s.last_seen,
               ST_X(ST_AsText(ST_Transform(l.location::geometry, 4326))) AS lon,
               ST_Y(ST_AsText(ST_Transform(l.location::geometry, 4326))) AS lat,
               l.updated_at AS location_updated_at
        FROM iot.devices d
        LEFT JOIN iot.state s ON s.device_id = d.device_id
        LEFT JOIN iot.location l ON l.device_id = d.device_id
        WHERE d.tenant_id = $1
        ORDER BY d.device_id
        """,
        tenant_id,
    )

async def get_device_by_id(conn: asyncpg.Connection, device_id: str, tenant_id: str) -> asyncpg.Record | None:
    return await conn.fetchval(
        """
        SELECT 1 
        FROM iot.devices 
        WHERE device_id=$1 
        AND tenant_id=$2
        """, 
        device_id, tenant_id
    )

async def is_belongs_to_tenant(conn: asyncpg.Connection, device_id: str, tenant_id: str) -> bool:
    return await conn.fetchval(
        """
        SELECT 1
        FROM iot.devices d
        JOIN iot.tenant t ON t.tenant_id = d.tenant_id
        WHERE d.device_id::text = $1 AND t.tenant_name = $2
        """, 
        device_id, tenant_id
    )

async def upsert_state(conn: asyncpg.Connection, *, device_id: str, rssi: int | None, snr: float | None, battery: float | None, online: str, ts) -> None:
    await conn.execute(
        """
        INSERT INTO iot.state(device_id, battery_level, status, rssi, snr, last_seen, updated_at)
        VALUES($1,$2,$3,$4,$5,$6,$6)
        ON CONFLICT (device_id)
        DO UPDATE SET battery_level=EXCLUDED.battery_level,
                      status=EXCLUDED.status,
                      rssi=EXCLUDED.rssi,
                      snr=EXCLUDED.snr,
                      last_seen=EXCLUDED.last_seen,
                      updated_at=EXCLUDED.updated_at
        """,
        device_id, battery, (online == "online"), rssi, snr, ts,
    )

async def upsert_location(conn: asyncpg.Connection, *, device_id: str, lat: float, lon: float, ts) -> None:
    await conn.execute(
        """
        INSERT INTO iot.location(device_id, location, updated_at)
        VALUES($1, ST_SetSRID(ST_MakePoint($3, $2), 4326)::geography, $4)
        ON CONFLICT (device_id)
        DO UPDATE SET location=EXCLUDED.location, updated_at=EXCLUDED.updated_at
        """,
        device_id, lat, lon, ts,
    )

async def get_markers(conn: asyncpg.Connection, tenant_id: str) -> Sequence[asyncpg.Record]:
    return await conn.fetch(
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