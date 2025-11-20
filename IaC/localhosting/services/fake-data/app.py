import argparse
import os
import random
import string
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def rand_id(prefix="device", n=4):
    return f"{prefix}-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

class FakeDevice:
    def __init__(self, device_id, broker_host, broker_port, env, tenant, client, humidity_base=45.0):
        self.id = device_id
        self.client = client
        self.env = env
        self.tenant = tenant
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.seq = 0
        self.humidity = humidity_base + random.uniform(-3, 3)
        self.rssi = -60 + random.randint(-15, 5)
        self.snr = 7.5 + random.uniform(-3, 3)
        self.battery = random.uniform(40.0, 100.0)
        self.lat = 54.842621 + random.uniform(-0.5, 0.5)
        self.lon = 83.087844 + random.uniform(-0.5, 0.5)
        self.online = "online"
        self.running = True
        self.topic_cmd = f"{env}/{tenant}/devices/{self.id}/command"
        self.topic_ack = f"{env}/{tenant}/devices/{self.id}/ack"

    def publish_humidity(self, retain=False):
        self.seq += 1
        self.humidity = clamp(self.humidity + random.uniform(-0.3, 0.3), 0.0, 100.0)
        payload = f"{self.id},{now_iso()},{self.humidity:.2f},{self.seq}"
        topic = f"{self.env}/{self.tenant}/sensors/{self.id}/humidity"
        self.client.publish(topic, payload=payload, qos=1, retain=retain)

    def publish_state(self, retain=True):
        self.rssi += random.randint(-1, 1)
        self.rssi = clamp(self.rssi, -100, -40)
        self.snr += random.uniform(-0.2, 0.2)
        self.battery = clamp(self.battery - random.uniform(0.0, 0.05), 5.0, 100.0)
        payload = f"{self.id},{now_iso()},{self.rssi},{self.snr:.2f},{self.battery:.1f},{self.online}"
        topic = f"{self.env}/{self.tenant}/sensors/{self.id}/state"
        self.client.publish(topic, payload=payload, qos=1, retain=retain)

    def publish_location(self, retain=True):
        self.lat += random.uniform(-0.0008, 0.0008)
        self.lon += random.uniform(-0.0008, 0.0008)
        payload = f"{self.id},{now_iso()},{self.lat:.6f},{self.lon:.6f}"
        topic = f"{self.env}/{self.tenant}/sensors/{self.id}/location"
        self.client.publish(topic, payload=payload, qos=1, retain=retain)

    def handle_command(self, payload: str):
        try:
            parts = payload.split(",", 3)
            command_id = parts[0]

            def ack():
                status = "ok"
                details = ""
                ack_payload = f"{command_id},{now_iso()},{status},{details}"
                self.client.publish(self.topic_ack, payload=ack_payload, qos=1, retain=False)

                cmd_type = parts[2].strip().upper()
                if cmd_type == "SLEEP":
                    self.online = "sleep"
                elif cmd_type == "WAKE":
                    self.online = "online"
                elif cmd_type == "OFFLINE":
                    self.online = "offline"

                print(f"[faker:{self.id}] command {command_id} processed: {cmd_type}")

            threading.Timer(0.5 + random.random(), ack).start()
        except Exception as e:
            command_id = "unknown"
            ack_payload = f"{command_id},{now_iso()},error,{str(e)}"
            self.client.publish(self.topic_ack, payload=ack_payload, qos=1, retain=False)

def main():
    parser = argparse.ArgumentParser(description="dev/fake queue")
    parser.add_argument("--broker-host", default=os.getenv("MQTT_HOST", "mosquitto"))
    parser.add_argument("--broker-port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD", ""))
    parser.add_argument("--env", default=os.getenv("ENV", "dev"))
    parser.add_argument("--tenant", default=os.getenv("TENANT", "fake"))
    parser.add_argument("--devices", type=int, default=int(os.getenv("DEVICES", "5")))
    parser.add_argument("--state-period", type=float, default=float(os.getenv("STATE_PERIOD", "5.0")))
    parser.add_argument("--loc-period", type=float, default=float(os.getenv("LOCATION_PERIOD", "10.0")))
    parser.add_argument("--humidity-period", type=float, default=float(os.getenv("HUMIDITY_PERIOD", "1.0")))
    args = parser.parse_args()

    client = mqtt.Client(client_id=f"faker-{random.randint(1000,9999)}", clean_session=True)
    if args.username:
        client.username_pw_set(args.username, args.password)

    devices = [
        FakeDevice(
            device_id=f"dev-{i:03d}",
            broker_host=args.broker_host,
            broker_port=args.broker_port,
            env=args.env,
            tenant=args.tenant,
            client=client,
            humidity_base=random.uniform(40, 60),
        )
        for i in range(args.devices)
    ]

    def on_connect(c: mqtt.Client, userdata, flags, rc):
        print(f"[faker] connected rc={rc}")
        for d in devices:
            c.subscribe(d.topic_cmd, qos=1)
            d.publish_state(retain=True)
            d.publish_location(retain=True)

    def on_message(c: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        for d in devices:
            if msg.topic == d.topic_cmd:
                d.handle_command(msg.payload.decode("utf-8", errors="ignore"))
                break

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(args.broker_host, args.broker_port, keepalive=30)
    threading.Thread(target=lambda: client.loop_forever(retry_first_connection=True), daemon=True).start()

    t0 = time.time()
    next_state = [t0 + random.uniform(0, args.state_period) for _ in devices]
    next_loc = [t0 + random.uniform(0, args.loc_period) for _ in devices]
    next_h = [t0 + random.uniform(0, args.humidity_period) for _ in devices]

    print(
        f"[faker] env={args.env} tenant={args.tenant} devices={len(devices)} "
        f"humidity_period={args.humidity_period}s state_period={args.state_period}s loc_period={args.loc_period}s"
    )

    try:
        while True:
            now = time.time()
            for i, d in enumerate(devices):
                if now >= next_h[i] and d.online == "online":
                    d.publish_humidity(retain=False)
                    next_h[i] = now + args.humidity_period

                if now >= next_state[i]:
                    d.publish_state(retain=True)
                    next_state[i] = now + args.state_period

                if now >= next_loc[i]:
                    d.publish_location(retain=True)
                    next_loc[i] = now + args.loc_period

            time.sleep(0.02)
    except KeyboardInterrupt:
        print("[faker] stopping...")

if __name__ == "__main__":
    main()
