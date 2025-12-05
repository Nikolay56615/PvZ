import asyncpg

async def insert_humidity(conn: asyncpg.Connection, *, device_id: str, ts, humidity: float, seq: int | None):
    await conn.execute(
        """
        INSERT INTO iot.monitoring_raw(device_id, sent_ts, humidity, seq)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT DO NOTHING
        """,
        device_id, ts, humidity, seq,
    )
    
async def query_humidity(conn: asyncpg.Connection, *, device_id: str, since, until):
    return await conn.fetch(
        """
        SELECT sent_ts, humidity 
        FROM iot.monitoring_raw 
        WHERE device_id=$1 AND sent_ts
        BETWEEN $2 AND $3 ORDER BY sent_ts
        """,
        device_id, since, until,
    )

async def query_humidity_range(conn: asyncpg.Connection, *, device_id: str, since, until):
    return await conn.fetch(
        """
        SELECT sent_ts, humidity
        FROM iot.monitoring_raw
        WHERE device_id=$1 AND sent_ts >= $2 AND sent_ts <= $3
        ORDER BY sent_ts
        """,
        device_id, since, until,
    )