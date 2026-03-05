from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

OnlineStatus = Literal["offline","sleep","online"]

class DeviceOut(BaseModel):
    device_id: str
    external_id: str | None = None
    model: str | None = None
    status: str | None = None
    rssi: int | None = None
    snr: float | None = None
    battery: float | None = None
    online: bool | None = None
    lat: float | None = None
    lon: float | None = None
    location_updated_at: datetime | None = None

class CommandIn(BaseModel):
    type: str
    params: dict | None = None
    retain: bool = False