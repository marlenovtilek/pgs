from datetime import datetime, timezone

from app.domain.entities.spot_event import SpotEventEntity
from app.domain.value_objects.spot_status import SpotStatus


def build_mock_camera_event(
    *,
    camera_code: str,
    spot_code: str,
    status: SpotStatus,
) -> SpotEventEntity:
    return SpotEventEntity(
        camera_code=camera_code,
        spot_code=spot_code,
        status=status,
        occurred_at=datetime.now(tz=timezone.utc),
    )
