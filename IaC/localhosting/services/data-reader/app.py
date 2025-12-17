import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    broker_host = os.getenv("MQTT_HOST", "5.129.250.254")
    broker_port = int(os.getenv("MQTT_PORT", "1883"))
    username = os.getenv("MQTT_USERNAME", "dynsec-admin")
    password = os.getenv("MQTT_PASSWORD", "change_me_admin")
    env = os.getenv("ENV", "dev")
    tenant = os.getenv("TENANT", "fake")

    default_topic = f"{env}/{tenant}/#"
    subscribe_topic = os.getenv("MQTT_SUB_TOPIC", default_topic)

    print(
        f"[sub] connecting to {broker_host}:{broker_port} "
        f"env={env} tenant={tenant} topic={subscribe_topic}"
    )

    client = mqtt.Client(
        client_id=f"simple-subscriber-{int(time.time())}",
        clean_session=True,
    )

    if username:
        client.username_pw_set(username, password)


    def on_connect(c: mqtt.Client, userdata, flags, rc):
        print(f"[sub] connected rc={rc}")
        if rc == 0:
            c.subscribe(subscribe_topic, qos=1)
            print(f"[sub] subscribed to {subscribe_topic}")
        else:
            print("[sub] connection failed, check host/port/creds")

    def on_disconnect(c: mqtt.Client, userdata, rc):
        print(f"[sub] disconnected rc={rc}")

    def on_message(c: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        try:
            payload_str = msg.payload.decode("utf-8", errors="replace")
        except Exception as e:
            payload_str = f"<decode error: {e}>"

        ts = now_iso()
        print(
            f"[{ts}] topic={msg.topic} qos={msg.qos} "
            f"payload={payload_str}"
        )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message


    try:
        client.connect(broker_host, broker_port, keepalive=30)
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        print("\n[sub] interrupted by user, exiting...")
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
