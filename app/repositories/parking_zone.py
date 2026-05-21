from typing import Protocol

from app.models.parking_zone import ParkingZone


class ParkingZoneRepository(Protocol):
    def create(self, zone: ParkingZone) -> ParkingZone:
        """Persist a parking zone."""
