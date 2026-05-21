from datetime import datetime

from pydantic import BaseModel

from app.domain.value_objects.spot_status import SpotStatus


class SpotEventRequest(BaseModel):
    spot_code: str
    status: SpotStatus
    detected_at: datetime
    source: str = "UNV_SERVICE"
    event_id: str | None = None
    payload: dict | None = None


class SpotEventResponse(BaseModel):
    success: bool
    dedup_key: str
    spot_code: str
    status: str
