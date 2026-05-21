from dataclasses import dataclass
from datetime import datetime

from app.domain.value_objects.spot_status import SpotStatus


@dataclass(slots=True)
class SpotEventEntity:
    spot_code: str
    status: SpotStatus
    occurred_at: datetime
    source: str
    event_id: str | None = None
    plate_number: str | None = None
    confidence: float | None = None
