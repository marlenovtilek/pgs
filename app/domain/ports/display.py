from typing import Protocol


class DisplayCommandPort(Protocol):
    async def show_zone_summary(
        self,
        *,
        display_code: str,
        zone_code: str,
        free_spots: int,
        arrow_direction: str,
        parking_symbol: str,
        display_text: str,
        message: str,
    ) -> None:
        """Send a summary command to a LED display."""
