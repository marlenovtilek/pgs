from typing import Protocol


class DisplayCommandPort(Protocol):
    async def show_sector_summary(
        self,
        *,
        display_code: str,
        sector_code: str,
        free_spots: int,
        arrow_direction: str,
        parking_symbol: str,
        display_text: str,
        message: str,
    ) -> None:
        """Send a summary command to a LED display."""
