from pydantic import BaseModel
from datetime import datetime

class RangeQuery(BaseModel):
    since: datetime
    until: datetime