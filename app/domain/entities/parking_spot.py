from dataclasses import dataclass

from app.domain.value_objects.spot_status import SpotStatus


@dataclass(slots=True)
class ParkingSpotEntity:
    spot_id: str
    sector_code: str
    row_code: str | None
    status: SpotStatus
    plate_number: str | None = None
