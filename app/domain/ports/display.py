from typing import Protocol

from app.domain.value_objects.arrow_direction import ArrowDirection


class DisplayCommandPort(Protocol):
    async def show_zone_summary(
        self,
        *,
        zone_code: str,
        free_spots: int,
        direction: ArrowDirection,
    ) -> None:
        """Send a summary command to a LED display."""
