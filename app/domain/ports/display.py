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
        device_code: str | None = None,
        device_host: str | None = None,
        device_port: int | None = None,
        device_protocol: str | None = None,
    ) -> None:
        """Send a summary command to a LED display."""
