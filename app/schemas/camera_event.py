from datetime import datetime
from pydantic import BaseModel
from app.domain.value_objects.spot_status import SpotStatus


class SimulateCameraEventRequest(BaseModel):
    camera_code: str
    spot_code: str
    status: SpotStatus
    detected_at: datetime
    source: str = "SIMULATOR"
    event_id: str | None = None
    payload: dict | None = None


class SimulateCameraEventResponse(BaseModel):
    success: bool
    dedup_key: str
    spot_code: str
    status: str
