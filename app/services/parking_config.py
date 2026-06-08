import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.value_objects.arrow_direction import ArrowDirection
from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay, guidance_display_zones
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.services.parking_codes import parse_parking_spot_code, camera_zone_code_from_spot_code


SPOT_RANGE_PATTERN = re.compile(r"^(?P<prefix>.*?)(?P<number>\d+)$")


@dataclass(slots=True)
class ParkingMapSeedResult:
    zones_created: int = 0
    spots_created: int = 0
    displays_created: int = 0
    spots_updated: int = 0
    spots_activated: int = 0
    spots_deactivated: int = 0
    displays_updated: int = 0


@dataclass(slots=True)
class ParkingBaseConfigSeedResult:
    floors_created: int = 0
    sectors_created: int = 0
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


def parse_sector_spec(value: str) -> tuple[str, list[str]]:
    if "=" not in value:
        raise ValueError("Sector spec must look like SECTOR=SPOT_START..SPOT_END.")

    sector_code, spot_range = value.split("=", maxsplit=1)
    sector_code = sector_code.strip()
    if not sector_code:
        raise ValueError("Sector spec does not include sector code.")

    return sector_code, expand_spot_range(spot_range.strip())


def seed_sector_display_config(
    db: Session,
    *,
    sector_codes: list[str],
    arrow_direction: ArrowDirection = ArrowDirection.AHEAD,
) -> ParkingBaseConfigSeedResult:
    result = ParkingBaseConfigSeedResult()

    for sector_code in sector_codes:
        floor_code, sector_letter = _split_sector_code(sector_code)
        floor = db.scalar(select(ParkingFloor).where(ParkingFloor.code == floor_code))
        if floor is None:
            floor = ParkingFloor(
                title=f"Floor {floor_code}",
                code=floor_code,
                sort_order=_sort_order_from_spot_code(floor_code),
                is_active=True,
            )
            db.add(floor)
            db.flush()
            result.floors_created += 1

        sector = db.scalar(select(ParkingSector).where(ParkingSector.code == sector_code))
        if sector is None:
            sector = ParkingSector(
                floor_id=floor.id,
                title=f"Sector {sector_code}",
                code=sector_code,
                sector_letter=sector_letter,
                sort_order=_sort_order_from_spot_code(sector_letter),
                is_active=True,
            )
            db.add(sector)
            db.flush()
            result.sectors_created += 1

        display_code = f"DISP-{sector_code}"
        display = db.scalar(select(GuidanceDisplay).where(GuidanceDisplay.code == display_code))
        if display is None:
            db.add(
                GuidanceDisplay(
                    title=f"Display {sector_code}",
                    code=display_code,
                    sector_id=sector.id,
                    arrow_direction=arrow_direction.value,
                    is_active=True,
                )
            )
            result.displays_created += 1

    db.commit()
    return result


def seed_sector_spots(
    db: Session,
    *,
    sector_code: str,
    spot_codes: list[str],
    initial_status: SpotStatus = SpotStatus.UNKNOWN,
    arrow_direction: ArrowDirection = ArrowDirection.AHEAD,
    update_existing_status: bool = False,
    deactivate_missing_spots: bool = False,
) -> ParkingMapSeedResult:
    result = ParkingMapSeedResult()

    floor_code, sector_letter = _split_sector_code(sector_code)
    floor = _get_or_create_floor(db, floor_code)
    sector = _get_or_create_sector(db, floor, sector_code, sector_letter)

    for spot_code in spot_codes:
        parsed = parse_parking_spot_code(spot_code)
        camera_zone_code = camera_zone_code_from_spot_code(spot_code) or sector_code
        zone_number = parsed.camera_zone_number if parsed is not None else camera_zone_code
        zone = db.scalar(
            select(ParkingZone).where(
                ParkingZone.sector_id == sector.id,
                ParkingZone.code == camera_zone_code,
            )
        )
        if zone is None:
            zone = ParkingZone(
                sector_id=sector.id,
                title=f"Camera Zone {camera_zone_code}",
                code=camera_zone_code,
                zone_number=zone_number or camera_zone_code,
                sort_order=_sort_order_from_spot_code(camera_zone_code),
                is_active=True,
            )
            db.add(zone)
            db.flush()
            result.zones_created += 1

        existing_spot = db.scalar(
            select(ParkingSpot).where(
                ParkingSpot.zone_id == zone.id,
                ParkingSpot.code == spot_code,
            )
        )
        if existing_spot is not None:
            if not existing_spot.is_active:
                existing_spot.is_active = True
                result.spots_activated += 1
            if update_existing_status and existing_spot.status != initial_status.value:
                existing_spot.status = initial_status.value
                result.spots_updated += 1
            continue

        db.add(
            ParkingSpot(
                zone_id=zone.id,
                code=spot_code,
                status=initial_status.value,
                sort_order=_sort_order_from_spot_code(spot_code),
                is_active=True,
            )
        )
        result.spots_created += 1

    display_code = f"DISP-{sector_code}"
    display = db.scalar(select(GuidanceDisplay).where(GuidanceDisplay.code == display_code))
    if display is None:
        display = GuidanceDisplay(
            title=f"Display {sector_code}",
            code=display_code,
            sector_id=sector.id,
            arrow_direction=arrow_direction.value,
            is_active=True,
        )
        db.add(display)
        db.flush()
        result.displays_created += 1
    elif not display.is_active:
        display.is_active = True
        result.displays_updated += 1

    _replace_display_zones_with_sector_zones(db, display=display, sector=sector)

    if deactivate_missing_spots:
        desired_spot_codes = set(spot_codes)
        existing_spots = db.scalars(
            select(ParkingSpot)
            .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
            .where(ParkingZone.sector_id == sector.id)
        ).all()
        for spot in existing_spots:
            if spot.code not in desired_spot_codes and spot.is_active:
                spot.is_active = False
                result.spots_deactivated += 1

    db.commit()
    return result


def deactivate_unlisted_displays(db: Session, *, active_sector_codes: set[str]) -> int:
    displays = db.execute(
        select(GuidanceDisplay, ParkingSector)
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
    ).all()

    updated = 0
    for display, sector in displays:
        should_be_active = sector.code in active_sector_codes
        if display.is_active != should_be_active:
            display.is_active = should_be_active
            updated += 1

    db.commit()
    return updated


def deactivate_unlisted_sector_spots(db: Session, *, active_sector_codes: set[str]) -> int:
    rows = db.execute(
        select(ParkingSpot, ParkingSector)
        .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
        .join(ParkingSector, ParkingZone.sector_id == ParkingSector.id)
    ).all()

    updated = 0
    for spot, sector in rows:
        if sector.code not in active_sector_codes and spot.is_active:
            spot.is_active = False
            updated += 1

    db.commit()
    return updated


def _sort_order_from_spot_code(spot_code: str) -> int:
    match = SPOT_RANGE_PATTERN.match(spot_code)
    if match is None:
        return 0
    return int(match.group("number"))


def _split_sector_code(sector_code: str) -> tuple[str, str]:
    if "-" not in sector_code:
        raise ValueError("Sector code must look like FLOOR-SECTOR, for example B1-A.")
    floor_code, sector_letter = sector_code.split("-", maxsplit=1)
    return floor_code, sector_letter


def _get_or_create_floor(
    db: Session,
    floor_code: str,
) -> ParkingFloor:
    floor = db.scalar(select(ParkingFloor).where(ParkingFloor.code == floor_code))
    if floor is not None:
        return floor

    floor = ParkingFloor(
        title=f"Floor {floor_code}",
        code=floor_code,
        sort_order=_sort_order_from_spot_code(floor_code),
        is_active=True,
    )
    db.add(floor)
    db.flush()
    return floor


def _get_or_create_sector(
    db: Session,
    floor: ParkingFloor,
    sector_code: str,
    sector_letter: str,
) -> ParkingSector:
    sector = db.scalar(select(ParkingSector).where(ParkingSector.code == sector_code))
    if sector is not None:
        return sector

    sector = ParkingSector(
        floor_id=floor.id,
        title=f"Sector {sector_code}",
        code=sector_code,
        sector_letter=sector_letter,
        sort_order=_sort_order_from_spot_code(sector_letter),
        is_active=True,
    )
    db.add(sector)
    db.flush()
    return sector


def _replace_display_zones_with_sector_zones(
    db: Session,
    *,
    display: GuidanceDisplay,
    sector: ParkingSector,
) -> None:
    zone_ids = db.scalars(
        select(ParkingZone.id)
        .where(
            ParkingZone.sector_id == sector.id,
            ParkingZone.is_active.is_(True),
        )
        .order_by(ParkingZone.sort_order, ParkingZone.code)
    ).all()
    db.execute(
        guidance_display_zones.delete().where(
            guidance_display_zones.c.display_id == display.id,
        )
    )
    for sort_order, zone_id in enumerate(zone_ids, start=1):
        db.execute(
            guidance_display_zones.insert().values(
                display_id=display.id,
                zone_id=zone_id,
                sort_order=sort_order,
            )
        )
