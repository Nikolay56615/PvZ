import asyncio
import logging
import uuid
from datetime import datetime, timezone

import asyncpg
from asyncio_mqtt import Client, MqttError

from .services.config import settings
from .db import get_pool
from .repositories import devices as devrepo
from .repositories import telemetry as telrepo
from .repositories import commands as cmdrepo

TOPIC_HUM = "+/+/sensors/+/humidity"
TOPIC_LOC = "+/+/sensors/+/location"
TOPIC_STATE = "+/+/sensors/+/state"
TOPIC_ACK = "+/+/devices/+/ack"

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
logger.setLevel(logging.DEBUG)


def _iso(ts: str):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _split_topic(topic: str):
    parts = str(topic).split("/")
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
    parts = line.split(",")
    if len(parts) < 3:
        raise ValueError(f"bad humidity payload: {line!r}")
    d, ts, h = parts[0], parts[1], parts[2]
    seq = int(parts[3]) if len(parts) > 3 and parts[3] else None
    await telrepo.insert_humidity(conn, device_id=d, ts=_iso(ts), humidity=float(h), seq=seq)


async def _handle_location(line: str, conn: asyncpg.Connection, device_id: str):
    parts = line.split(",")
    if len(parts) < 4:
        raise ValueError(f"bad location payload: {line!r}")
    d, ts, lat, lon = parts[0], parts[1], parts[2], parts[3]
    if d != device_id:
        return
    await devrepo.upsert_location(conn, device_id=d, lat=float(lat), lon=float(lon), ts=_iso(ts))


async def _handle_state(line: str, conn: asyncpg.Connection, device_id: str):
    parts = line.split(",")
    if len(parts) < 6:
        raise ValueError(f"bad state payload: {line!r}")
    d, ts, rssi, snr, bat, online = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
    if d != device_id:
        return
    await devrepo.upsert_state(
        conn,
        device_id=d,
        rssi=int(rssi),
        snr=float(snr),
        battery=float(bat),
        online=online,
        ts=_iso(ts),
    )


async def _handle_ack(line: str, conn: asyncpg.Connection):
    parts = line.split(",", 3)
    if not parts:
        raise ValueError(f"bad ack payload: {line!r}")
    cmd_id = parts[0]
    status = parts[2] if len(parts) > 2 else "unknown"
    details = parts[3] if len(parts) > 3 else None
    await cmdrepo.ack_command(conn, cmd_id=cmd_id, status=status, error=details)


async def publish_command(
    *,
    tenant_id: str,
    device_id: str,
    type_: str,
    params: dict | None = None,
    retain: bool = False,
) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not await _device_belongs(conn, device_id, tenant_id):
            raise ValueError("Device does not belong to tenant")
        await _set_rls(conn, tenant_id)

        cmd_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = f"{cmd_id},{ts},{type_},{params or ''}"
        topic = f"{settings.app_env}/{tenant_id}/devices/{device_id}/command"

        await cmdrepo.create_command(
            conn,
            device_id=device_id,
            cmd_id=cmd_id,
            type_=type_,
            params=params or {},
            retain=retain,
        )
        logger.info("Created command %s for device %s tenant %s", cmd_id, device_id, tenant_id)

    async with Client(
        settings.mqtt_host,
        settings.mqtt_port,
        username=settings.mqtt_username or None,
        password=settings.mqtt_password or None,
        keepalive=30,
    ) as client:
        logger.info("Publishing command %s to topic %s", cmd_id, topic)
        await client.publish(topic, payload.encode("utf-8"), qos=1, retain=retain)

    async with pool.acquire() as conn:
        await _set_rls(conn, tenant_id)
        await cmdrepo.mark_sent(conn, cmd_id=cmd_id)
    return cmd_id


async def run_mqtt_forever():
    pool = await get_pool()

    while True:
        logger.info("Starting MQTT runtime...")
        try:
            logger.info("Connecting to MQTT broker at %s:%d (env=%s)", settings.mqtt_host, settings.mqtt_port, settings.app_env)

            client = Client(
                settings.mqtt_host,
                settings.mqtt_port,
                username=settings.mqtt_username or None,
                password=settings.mqtt_password or None,
                keepalive=30,
            )

            async with asyncio.timeout(10):
                async with client as client:
                    logger.info("Connected to MQTT broker")

                    async with client.unfiltered_messages() as messages:
                        await client.subscribe(TOPIC_HUM, qos=1)
                        await client.subscribe(TOPIC_LOC, qos=1)
                        await client.subscribe(TOPIC_STATE, qos=1)
                        await client.subscribe(TOPIC_ACK, qos=1)

                        logger.info("Subscribed to topics")

                        logger.info("MQTT runtime started, listening for messages...")
                        async for msg in messages:
                            try:
                                topic_str = str(msg.topic)
                                meta = _split_topic(topic_str)
                                if not meta:
                                    logger.debug("Ignoring topic with insufficient parts: %s", topic_str)
                                    continue

                                env, tenant_name, kind, device_id, leaf = meta

                                logger.debug("Message meta env=%s tenant=%s kind=%s device=%s leaf=%s", env, tenant_name, kind, device_id, leaf)

                                if env != settings.app_env:
                                    logger.info("Ignoring message from env=%s because app_env=%s", env, settings.app_env)
                                    continue

                                payload = msg.payload.decode("utf-8", errors="ignore")

                                async with pool.acquire() as conn:
                                    belongs = await _device_belongs(conn, device_id, tenant_name)
                                    if not belongs:
                                        logger.info("Skipping message: device %s does not belong to tenant %s", device_id, tenant_name)
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
                                    else:
                                        logger.debug("Unknown leaf %s, ignoring", leaf)

                            except Exception:
                                logger.exception("Error processing MQTT message")

        except TimeoutError:
            logger.exception("Timeout while connecting/subscribing to MQTT, retrying in 2s")
            await asyncio.sleep(2)

        except MqttError:
            logger.exception("MQTT connection/protocol error, retrying in 2s")
            await asyncio.sleep(2)

        except Exception:
            logger.exception("MQTT runtime crashed unexpectedly, retrying in 2s")
            await asyncio.sleep(2)
