from typing import Protocol

from app.domain.entities.spot_event import SpotEventEntity


class CameraEventSourcePort(Protocol):
    async def consume(self) -> SpotEventEntity | None:
        """Read the next camera event from a vendor-specific source."""
