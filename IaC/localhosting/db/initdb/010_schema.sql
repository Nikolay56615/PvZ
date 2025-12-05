CREATE SCHEMA IF NOT EXISTS iot;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'permission_level') THEN
    CREATE TYPE iot.permission_level AS ENUM ('OWNER','ADMIN','OPERATOR','VIEWER');
  END IF;
END$$;

CREATE OR REPLACE FUNCTION iot.tg_set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END$$;

CREATE TABLE IF NOT EXISTS iot.tenant (
  tenant_id   uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_name text NOT NULL UNIQUE,
  tenant_owner text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER tr_tenant_updated
BEFORE UPDATE ON iot.tenant
FOR EACH ROW EXECUTE FUNCTION iot.tg_set_updated_at();

CREATE TABLE IF NOT EXISTS iot.users (
  user_id     uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        varchar(120) NOT NULL,
  password    text NOT NULL,
  permissions iot.permission_level NOT NULL DEFAULT 'VIEWER',
  tenant_id   uuid REFERENCES iot.tenant(tenant_id) ON DELETE SET NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER tr_users_updated
BEFORE UPDATE ON iot.users
FOR EACH ROW EXECUTE FUNCTION iot.tg_set_updated_at();

CREATE TABLE IF NOT EXISTS iot.devices (
  device_id      uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  installation_id uuid,
  model          varchar(64),
  tenant_id      uuid NOT NULL REFERENCES iot.tenant(tenant_id) ON DELETE CASCADE,
  status         text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS devices_tenant_idx ON iot.devices(tenant_id);
CREATE TRIGGER tr_devices_updated
BEFORE UPDATE ON iot.devices
FOR EACH ROW EXECUTE FUNCTION iot.tg_set_updated_at();

CREATE TABLE IF NOT EXISTS iot.state (
  device_id     uuid PRIMARY KEY REFERENCES iot.devices(device_id) ON DELETE CASCADE,
  battery_level double precision,
  status        boolean,
  updated_at    timestamptz NOT NULL DEFAULT now(),
  rssi          integer,
  snr           double precision,
  last_seen     timestamptz
);
CREATE INDEX IF NOT EXISTS state_updated_idx ON iot.state(updated_at DESC);

CREATE TABLE IF NOT EXISTS iot.location (
  device_id  uuid PRIMARY KEY REFERENCES iot.devices(device_id) ON DELETE CASCADE,
  location   geography(Point, 4326),
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS location_geom_idx ON iot.location USING GIST(location);

CREATE TABLE IF NOT EXISTS iot.monitoring_raw (
  device_id uuid NOT NULL REFERENCES iot.devices(device_id) ON DELETE CASCADE,
  humidity  double precision NOT NULL,
  seq       bigint,
  sent_ts   timestamptz NOT NULL,
  PRIMARY KEY (device_id, sent_ts)
);

SELECT create_hypertable('iot.monitoring_raw', 'sent_ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS monitoring_raw_ts_idx ON iot.monitoring_raw (sent_ts DESC);
CREATE INDEX IF NOT EXISTS monitoring_raw_device_ts_idx ON iot.monitoring_raw (device_id, sent_ts DESC);


DROP MATERIALIZED VIEW IF EXISTS iot.monitoring_nm CASCADE;
CREATE MATERIALIZED VIEW iot.monitoring_nm
WITH (timescaledb.continuous) AS
SELECT
  device_id,
  time_bucket('5 minutes', sent_ts) AS bucket,
  avg(humidity) AS humidity_avg
FROM iot.monitoring_raw
GROUP BY device_id, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
  'iot.monitoring_nm',
  start_offset => INTERVAL '1 day',
  end_offset   => INTERVAL '1 minute',
  schedule_interval => INTERVAL '5 minutes'
);

CREATE UNIQUE INDEX IF NOT EXISTS monitoring_nm_pk
  ON iot.monitoring_nm (device_id, bucket);
CREATE INDEX IF NOT EXISTS monitoring_nm_bucket_idx
  ON iot.monitoring_nm (bucket DESC);


CREATE TABLE IF NOT EXISTS iot.device_commands (
  cmd_id     uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  device_id  uuid NOT NULL REFERENCES iot.devices(device_id) ON DELETE CASCADE,
  issued_ts  timestamptz NOT NULL DEFAULT now(),
  sent_ts    timestamptz,
  ack_ts     timestamptz,
  type       text NOT NULL,
  params     jsonb NOT NULL DEFAULT '{}'::jsonb,
  retain     boolean NOT NULL DEFAULT FALSE,
  status     text,
  error      text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS device_commands_device_idx ON iot.device_commands(device_id);
CREATE INDEX IF NOT EXISTS device_commands_issued_idx ON iot.device_commands(issued_ts DESC);


CREATE OR REPLACE VIEW iot.device_overview AS
SELECT
  d.device_id,
  d.tenant_id,
  d.model,
  d.status AS device_status,
  s.battery_level,
  s.status AS online,
  s.rssi,
  s.snr,
  s.last_seen,
  l.location,
  l.updated_at AS location_updated_at
FROM iot.devices d
LEFT JOIN iot.state s    ON s.device_id = d.device_id
LEFT JOIN iot.location l ON l.device_id = d.device_id;
