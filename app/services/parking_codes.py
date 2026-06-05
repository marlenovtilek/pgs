import re
from dataclasses import dataclass


LEGACY_PARKING_SPOT_CODE_PATTERN = re.compile(
    r"^(?P<level>[A-Za-z]\d+)-(?P<zone>[A-Za-z]+)-?(?P<number>\d+)$"
)
PARKING_SPOT_CODE_PATTERN = re.compile(
    r"^(?P<level>[A-Za-z]\d+)-(?P<sector>[A-Za-z]+)-(?P<camera_zone>\d+)-(?P<number>\d+)$"
)
LEGACY_CAMERA_ZONE_SIZE = 6


@dataclass(frozen=True, slots=True)
class ParsedParkingSpotCode:
    level_code: str
    sector_letter: str
    camera_zone_number: str | None
    spot_number: str

    @property
    def sector_code(self) -> str:
        return f"{self.level_code}-{self.sector_letter}"

    @property
    def camera_zone_code(self) -> str:
        if self.camera_zone_number is None:
            return self.sector_code
        return f"{self.sector_code}-{self.camera_zone_number}"


def parse_parking_spot_code(spot_code: str) -> ParsedParkingSpotCode | None:
    match = PARKING_SPOT_CODE_PATTERN.match(spot_code)
    if match is not None:
        return ParsedParkingSpotCode(
            level_code=match.group("level"),
            sector_letter=match.group("sector"),
            camera_zone_number=match.group("camera_zone"),
            spot_number=match.group("number"),
        )

    legacy_match = LEGACY_PARKING_SPOT_CODE_PATTERN.match(spot_code)
    if legacy_match is None:
        return None

    spot_number = int(legacy_match.group("number"))
    if spot_number < 1:
        return None

    camera_zone_index = (spot_number - 1) // LEGACY_CAMERA_ZONE_SIZE + 1
    camera_zone_spot_number = (spot_number - 1) % LEGACY_CAMERA_ZONE_SIZE + 1

    return ParsedParkingSpotCode(
        level_code=legacy_match.group("level"),
        sector_letter=legacy_match.group("zone"),
        camera_zone_number=f"{camera_zone_index:02d}",
        spot_number=str(camera_zone_spot_number),
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
