from typing import Protocol

from app.domain.value_objects.spot_status import SpotStatus


class StateStorePort(Protocol):
    async def set_spot_status(self, *, spot_code: str, status: SpotStatus) -> None:
        """Persist hot spot state in a fast state store."""

    async def get_zone_free_count(self, *, zone_code: str) -> int:
        """Return the latest free places count for a zone."""
