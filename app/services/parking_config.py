import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.value_objects.arrow_direction import ArrowDirection
from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone


SPOT_RANGE_PATTERN = re.compile(r"^(?P<prefix>.*?)(?P<number>\d+)$")


@dataclass(slots=True)
class ParkingMapSeedResult:
    zones_created: int = 0
    rows_created: int = 0
    spots_created: int = 0
    displays_created: int = 0


def expand_spot_range(value: str) -> list[str]:
    if ".." not in value:
        return [value]

    start, end = value.split("..", maxsplit=1)
    start_match = SPOT_RANGE_PATTERN.match(start)
    end_match = SPOT_RANGE_PATTERN.match(end)

    if start_match is None or end_match is None:
        raise ValueError(f"Invalid spot range: {value}")

    if start_match.group("prefix") != end_match.group("prefix"):
        raise ValueError(f"Spot range prefixes do not match: {value}")

    start_number = int(start_match.group("number"))
    end_number = int(end_match.group("number"))
    if end_number < start_number:
        raise ValueError(f"Spot range end is smaller than start: {value}")

    prefix = start_match.group("prefix")
    width = len(start_match.group("number"))

    return [
        f"{prefix}{number:0{width}d}"
        for number in range(start_number, end_number + 1)
    ]


def parse_zone_spec(value: str) -> tuple[str, list[str]]:
    if "=" not in value:
        raise ValueError("Zone spec must look like ZONE=SPOT_START..SPOT_END.")

    zone_code, spot_range = value.split("=", maxsplit=1)
    zone_code = zone_code.strip()
    if not zone_code:
        raise ValueError("Zone spec does not include zone code.")

    return zone_code, expand_spot_range(spot_range.strip())


def seed_zone_spots(
    db: Session,
    *,
    zone_code: str,
    spot_codes: list[str],
    initial_status: SpotStatus = SpotStatus.UNKNOWN,
    arrow_direction: ArrowDirection = ArrowDirection.AHEAD,
) -> ParkingMapSeedResult:
    result = ParkingMapSeedResult()

    zone = db.scalar(select(ParkingZone).where(ParkingZone.code == zone_code))
    if zone is None:
        zone = ParkingZone(
            title=f"Zone {zone_code}",
            code=zone_code,
            level=None,
            is_active=True,
        )
        db.add(zone)
        db.flush()
        result.zones_created += 1

    row = db.scalar(
        select(ParkingRow).where(
            ParkingRow.zone_id == zone.id,
            ParkingRow.code == zone_code,
        )
    )
    if row is None:
        row = ParkingRow(
            zone_id=zone.id,
            title=f"Row {zone_code}",
            code=zone_code,
            sort_order=0,
            is_active=True,
        )
        db.add(row)
        db.flush()
        result.rows_created += 1

    for spot_code in spot_codes:
        existing_spot = db.scalar(
            select(ParkingSpot).where(
                ParkingSpot.row_id == row.id,
                ParkingSpot.code == spot_code,
            )
        )
        if existing_spot is not None:
            continue

        db.add(
            ParkingSpot(
                row_id=row.id,
                code=spot_code,
                status=initial_status.value,
                sort_order=_sort_order_from_spot_code(spot_code),
                is_active=True,
            )
        )
        result.spots_created += 1

    display_code = f"DISP-{zone_code}"
    display = db.scalar(select(GuidanceDisplay).where(GuidanceDisplay.code == display_code))
    if display is None:
        db.add(
            GuidanceDisplay(
                title=f"Display {zone_code}",
                code=display_code,
                zone_id=zone.id,
                arrow_direction=arrow_direction.value,
                is_active=True,
            )
        )
        result.displays_created += 1

    db.commit()
    return result


def _sort_order_from_spot_code(spot_code: str) -> int:
    match = SPOT_RANGE_PATTERN.match(spot_code)
    if match is None:
        return 0
    return int(match.group("number"))
