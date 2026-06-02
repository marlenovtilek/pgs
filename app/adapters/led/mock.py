from dataclasses import dataclass


@dataclass(slots=True)
class LedCommand:
    display_code: str
    zone_code: str
    free_spots: int
    arrow_direction: str
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
        message: str,
    ) -> None:
        self.commands.append(
            LedCommand(
                display_code=display_code,
                zone_code=zone_code,
                free_spots=free_spots,
                arrow_direction=arrow_direction,
                message=message,
            )
        )


mock_led_adapter = MockLedDisplayAdapter()
