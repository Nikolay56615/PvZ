from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

OnlineStatus = Literal["offline", "sleep", "online"]

class Device(BaseModel):
    device_id: str
    tenant_id: str
    model: str | None = None
    status: str | None = None

class StateSnapshot(BaseModel):
    device_id: str
    ts: datetime
    rssi: int | None = None
    snr: float | None = None
    battery: float | None = None
    online: OnlineStatus

class LocationSnapshot(BaseModel):
    device_id: str
    ts: datetime
    lat: float
    lon: float

class HumidityRow(BaseModel):
    device_id: str
    ts: datetime
    humidity: float
    seq: int | None = None

class CommandOut(BaseModel):
    command_id: str
    device_id: str
    ts: datetime
    type: str
    additional: dict | None = None

class CommandAck(BaseModel):
    command_id: str
    ts: datetime
    status: str
    details: str | None = None