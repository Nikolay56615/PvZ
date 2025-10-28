import asyncpg

async def create_command(conn: asyncpg.Connection, *, device_id: str, cmd_id: str, type_: str, params: dict, retain: bool = False):
    await conn.execute(
        """
        INSERT INTO iot.device_commands(cmd_id, device_id, type, params, retain)
        VALUES($1,$2,$3,$4,$5)
        ON CONFLICT DO NOTHING
        """,
        cmd_id, device_id, type_, params, retain,
    )

async def ack_command(conn: asyncpg.Connection, *, cmd_id: str, status: str, error: str | None):
    await conn.execute(
        """
        UPDATE iot.device_commands
        SET status=$2, ack_ts=now(), error=$3
        WHERE cmd_id=$1
        """,
        cmd_id, status, error,
    )

async def mark_sent(conn: asyncpg.Connection, *, cmd_id: str):
    await conn.execute(
        """
        UPDATE iot.device_commands
        SET sent_ts = now()
        WHERE cmd_id = $1
        """,
        cmd_id,
    )