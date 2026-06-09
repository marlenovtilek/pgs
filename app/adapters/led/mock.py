from dataclasses import dataclass


@dataclass(slots=True)
class LedCommand:
    display_code: str
    sector_code: str
    free_spots: int
    arrow_direction: str
    parking_symbol: str
    display_text: str
    message: str
    device_code: str | None = None
    device_host: str | None = None
    device_port: int | None = None
    device_protocol: str | None = None


class MockLedDisplayAdapter:
    def __init__(self) -> None:
        self.commands: list[LedCommand] = []

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
        self.commands.append(
            LedCommand(
                display_code=display_code,
                sector_code=sector_code,
                free_spots=free_spots,
                arrow_direction=arrow_direction,
                parking_symbol=parking_symbol,
                display_text=display_text,
                message=message,
                device_code=device_code,
                device_host=device_host,
                device_port=device_port,
                device_protocol=device_protocol,
            )
        )


mock_led_adapter = MockLedDisplayAdapter()
