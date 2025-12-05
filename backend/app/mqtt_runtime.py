import asyncio
from asyncio_mqtt import Client, MqttError
from datetime import datetime, timezone
from .services.config import settings
from .db import get_pool
from .repositories import devices as devrepo
from .repositories import telemetry as telrepo
from .repositories import commands as cmdrepo
import asyncpg
import uuid

TOPIC_HUM = "+/+/sensors/+/humidity"
TOPIC_LOC = "+/+/sensors/+/location"
TOPIC_STATE = "+/+/sensors/+/state"
TOPIC_ACK = "+/+/devices/+/ack"

def _iso(ts: str):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def _split_topic(topic: str):
    parts = topic.split("/")
    if len(parts) < 5:
        return None
    env = parts[0]
    tenant = parts[1]
    kind = parts[2]
    device = parts[3]
    leaf = parts[4]
    return env, tenant, kind, device, leaf

async def _set_rls(conn: asyncpg.Connection, tenant_name: str):
    try:
        await conn.execute("SET LOCAL app.tenant = $1", tenant_name)
    except Exception:
        pass

async def _device_belongs(conn: asyncpg.Connection, device_id: str, tenant_name: str) -> bool:
    return bool(await devrepo.is_belongs_to_tenant(conn, device_id, tenant_name))

async def _handle_humidity(line: str, conn: asyncpg.Connection):
    d, ts, h, *rest = line.split(",", 3)
    seq = int(rest[0]) if rest and rest[0] else None
    await telrepo.insert_humidity(conn, device_id=d, ts=_iso(ts), humidity=float(h), seq=seq)

async def _handle_location(line: str, conn: asyncpg.Connection, device_id: str):
    d, ts, lat, lon = line.split(",", 3)
    if d != device_id:
        return
    await devrepo.upsert_location(conn, device_id=d, lat=float(lat), lon=float(lon), ts=_iso(ts))

async def _handle_state(line: str, conn: asyncpg.Connection, device_id: str):
    d, ts, rssi, snr, bat, online = line.split(",", 5)
    if d != device_id:
        return
    await devrepo.upsert_state(conn, device_id=d, rssi=int(rssi), snr=float(snr), battery=float(bat), online=online, ts=_iso(ts))

async def _handle_ack(line: str, conn: asyncpg.Connection):
    parts = line.split(",", 3)
    cmd_id = parts[0]
    status = parts[2] if len(parts) > 2 else "unknown"
    details = parts[3] if len(parts) > 3 else None
    await cmdrepo.ack_command(conn, cmd_id=cmd_id, status=status, error=details)

async def publish_command(*, tenant_id: str, device_id: str, type_: str, params: dict | None = None, retain: bool = False) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not await _device_belongs(conn, device_id, tenant_id):
            raise ValueError("Device does not belong to tenant")
        await _set_rls(conn, tenant_id)

        cmd_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = f"{cmd_id},{ts},{type_},{params or ''}"
        topic = f"{settings.app_env}/{tenant_id}/devices/{device_id}/command"

        await cmdrepo.create_command(conn, device_id=device_id, cmd_id=cmd_id, type_=type_, params=params or {}, retain=retain)

    async with Client(settings.mqtt_host, settings.mqtt_port, username=settings.mqtt_username or None, password=settings.mqtt_password or None) as client:
        await client.publish(topic, payload.encode("utf-8"), qos=1, retain=retain)

    async with pool.acquire() as conn:
        await _set_rls(conn, tenant_id)
        await cmdrepo.mark_sent(conn, cmd_id=cmd_id)
    return cmd_id

async def run_mqtt_forever():
    while True:
        try:
            async with Client(settings.mqtt_host, settings.mqtt_port, username=settings.mqtt_username or None, password=settings.mqtt_password or None) as client:
                await client.subscribe([(TOPIC_HUM,1),(TOPIC_LOC,1),(TOPIC_STATE,1),(TOPIC_ACK,1)])
                pool = await get_pool()
                async with client.unfiltered_messages() as messages:
                    async for msg in messages:
                        try:
                            meta = _split_topic(msg.topic)
                            if not meta:
                                continue
                            env, tenant_name, kind, device_id, leaf = meta

                            if env != settings.app_env:
                                continue

                            payload = msg.payload.decode("utf-8", errors="ignore")
                            async with pool.acquire() as conn:
                                if leaf != "ack":
                                    if not await _device_belongs(conn, device_id, tenant_name):
                                        continue
                                else:
                                    if not await _device_belongs(conn, device_id, tenant_name):
                                        continue

                                await _set_rls(conn, tenant_name)

                                if leaf == "humidity":
                                    await _handle_humidity(payload, conn)
                                elif leaf == "location":
                                    await _handle_location(payload, conn, device_id)
                                elif leaf == "state":
                                    await _handle_state(payload, conn, device_id)
                                elif leaf == "ack":
                                    await _handle_ack(payload, conn)
                        except Exception:
                            pass
        except MqttError:
            await asyncio.sleep(2)
