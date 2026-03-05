import asyncio
import contextlib
import json
import uuid
from contextlib import asynccontextmanager
from asyncio_mqtt import Client, MqttError
from .config import settings

class DynSecError(Exception):
    pass

@asynccontextmanager
async def _ctrl_client():
    try:
        client = Client(
            settings.mqtt_host,
            settings.mqtt_port,
            username=settings.dynsec_admin_username or settings.mqtt_username or None,
            password=settings.dynsec_admin_password or settings.mqtt_password or None,
        )
    except Exception as e:
        raise DynSecError(f"MQTT client init failed: {e}")

    try:
        await client.connect()
    except Exception as e:
        raise DynSecError(f"MQTT client connect failed: {e}")

    try:
        yield client
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

async def dynsec_call(commands: list[dict], timeout: float = 5.0) -> dict:
    if not settings.dynsec_enabled:
        raise DynSecError("Dynamic security disabled")

    correlation = str(uuid.uuid4())
    payload = {"commands": commands, "correlationData": correlation}

    async with _ctrl_client() as c:
        await c.subscribe(settings.dynsec_response_topic, qos=1)

        fut = asyncio.get_event_loop().create_future()

        async with c.unfiltered_messages() as messages:
            async def reader():
                async for msg in messages:
                    try:
                        data = json.loads(msg.payload.decode("utf-8"))
                    except Exception:
                        continue
                    if data.get("correlationData") == correlation:
                        if not fut.done():
                            fut.set_result(data)
                            return

            task = asyncio.create_task(reader())
            try:
                await c.publish(settings.dynsec_control_topic, json.dumps(payload).encode("utf-8"), qos=1)
                resp = await asyncio.wait_for(fut, timeout=timeout)
                results = resp.get("results", [])
                for r in results:
                    if r.get("error"):
                        raise DynSecError(r["error"])
                return resp
            finally:
                task.cancel()
                with contextlib.suppress(Exception):
                    await task
