import re
from dataclasses import dataclass


PARKING_SPOT_CODE_PATTERN = re.compile(
    r"^(?P<level>[A-Za-z]\d+)-(?P<sector>[A-Za-z]+)-(?P<camera_zone>\d+)-(?P<number>\d+)$"
)


@dataclass(frozen=True, slots=True)
class ParsedParkingSpotCode:
    level_code: str
    sector_letter: str
    camera_zone_number: str
    spot_number: str

    @property
    def sector_code(self) -> str:
        return f"{self.level_code}-{self.sector_letter}"

    @property
    def camera_zone_code(self) -> str:
        return f"{self.sector_code}-{self.camera_zone_number}"


def parse_parking_spot_code(spot_code: str) -> ParsedParkingSpotCode | None:
    match = PARKING_SPOT_CODE_PATTERN.match(spot_code)
    if match is None:
        return None

    return ParsedParkingSpotCode(
        level_code=match.group("level"),
        sector_letter=match.group("sector"),
        camera_zone_number=match.group("camera_zone"),
        spot_number=match.group("number"),
    )


def is_new_parking_spot_code(spot_code: str) -> bool:
    return PARKING_SPOT_CODE_PATTERN.match(spot_code) is not None


def sector_code_from_spot_code(spot_code: str) -> str | None:
    parsed = parse_parking_spot_code(spot_code)
    if parsed is None:
        return None
    return parsed.sector_code


def camera_zone_code_from_spot_code(spot_code: str) -> str | None:
    parsed = parse_parking_spot_code(spot_code)
    if parsed is None:
        return None
    return parsed.camera_zone_code
