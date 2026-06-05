from dataclasses import dataclass


@dataclass(slots=True)
class LedCommand:
    display_code: str
    zone_code: str
    free_spots: int
    arrow_direction: str
    parking_symbol: str
    display_text: str
    message: str


class MockLedDisplayAdapter:
    def __init__(self) -> None:
        self.commands: list[LedCommand] = []

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
        self.commands.append(
            LedCommand(
                display_code=display_code,
                zone_code=zone_code,
                free_spots=free_spots,
                arrow_direction=arrow_direction,
                parking_symbol=parking_symbol,
                display_text=display_text,
                message=message,
            )
        )


mock_led_adapter = MockLedDisplayAdapter()
