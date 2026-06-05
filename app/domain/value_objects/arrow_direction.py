from enum import StrEnum


class ArrowDirection(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    AHEAD = "AHEAD"
    FULL = "FULL"


CONFIGURABLE_ARROW_DIRECTIONS = (
    ArrowDirection.LEFT,
    ArrowDirection.RIGHT,
    ArrowDirection.AHEAD,
)

ARROW_DIRECTION_CHOICES = [
    (ArrowDirection.LEFT.value, "Left"),
    (ArrowDirection.RIGHT.value, "Right"),
    (ArrowDirection.AHEAD.value, "Ahead"),
]


def is_configurable_arrow_direction(value: str) -> bool:
    return value in {direction.value for direction in CONFIGURABLE_ARROW_DIRECTIONS}


def resolve_display_arrow_direction(configured_direction: str, free_spots: int) -> ArrowDirection:
    return ArrowDirection(configured_direction)
