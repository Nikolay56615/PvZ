import asyncio
import uuid
from asyncio_mqtt import Client, MqttError
from datetime import datetime, timezone
from .config import settings
from .db import get_pool
from .repositories import devices as devrepo
from .repositories import telemetry as telrepo
from .repositories import commands as cmdrepo

TOPIC_HUM = "+/+/sensors/+/humidity"
TOPIC_LOC = "+/+/sensors/+/location"
TOPIC_STATE = "+/+/sensors/+/state"
TOPIC_ACK = "+/+/devices/+/ack"
TIME = "+00:00"

async def _handle_humidity(line: str, conn):
    d, ts, h, *rest = line.split(",")
    seq = int(rest[0]) if rest and rest[0] else None
    ts_dt = datetime.fromisoformat(ts.replace("Z", TIME))
    await telrepo.insert_humidity(conn, device_id=d, ts=ts_dt, humidity=float(h), seq=seq)

async def _handle_location(line: str, conn):
    d, ts, lat, lon = line.split(",")
    ts_dt = datetime.fromisoformat(ts.replace("Z", TIME))
    await devrepo.upsert_location(conn, device_id=d, lat=float(lat), lon=float(lon), ts=ts_dt)

async def _handle_state(line: str, conn):
    d, ts, rssi, snr, bat, online = line.split(",")
    ts_dt = datetime.fromisoformat(ts.replace("Z", TIME))
    await devrepo.upsert_state(conn, device_id=d, rssi=int(rssi), snr=float(snr), battery=float(bat), online=online, ts=ts_dt)
    
async def _handle_ack(line: str, conn):
    parts = line.split(",", 3)
    cmd_id = parts[0]
    status = parts[2] if len(parts) > 2 else "unknown"
    details = parts[3] if len(parts) > 3 else None
    await cmdrepo.ack_command(conn, cmd_id=cmd_id, status=status, error=details)

async def publish_command(*, tenant_id: str, device_id: str, type_: str, params: dict | None = None, retain: bool = False) -> str:

    cmd_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = f"{cmd_id},{ts},{type_},{params or ''}"
    topic = f"{settings.app_env}/{tenant_id}/devices/{device_id}/command"


    pool = await get_pool()
    async with pool.acquire() as conn:
        await cmdrepo.create_command(conn, device_id=device_id, cmd_id=cmd_id, type_=type_, params=params or {}, retain=retain)


    async with Client(settings.mqtt_host, settings.mqtt_port, username=settings.mqtt_username or None, password=settings.mqtt_password or None) as client:
        await client.publish(topic, payload.encode("utf-8"), qos=1, retain=retain)


    async with pool.acquire() as conn:
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
                        topic = msg.topic
                        payload = msg.payload.decode("utf-8", errors="ignore")
                        async with pool.acquire() as conn:
                            if topic.endswith("/humidity"):
                                await _handle_humidity(payload, conn)
                            elif topic.endswith("/location"):
                                await _handle_location(payload, conn)
                            elif topic.endswith("/state"):
                                await _handle_state(payload, conn)
                            elif topic.endswith("/ack"):
                                await _handle_ack(payload, conn)
                                
        except MqttError as e:
            print(f"[mqtt_runtime] MQTT error: {e}")
            await asyncio.sleep(2)