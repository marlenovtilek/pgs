from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.spot_event import SpotEventRequest
from app.services.parking_codes import (
    camera_zone_code_from_spot_code,
    is_new_parking_spot_code,
    parse_parking_spot_code,
    sector_code_from_spot_code,
)


MQTT_STATUS_MAP = {
    "free": SpotStatus.FREE,
    "occupied": SpotStatus.OCCUPIED,
    "offline": SpotStatus.OFFLINE,
    "unknown": SpotStatus.UNKNOWN,
}


def spot_id_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 4:
        return None
    if parts[0] != "parking" or parts[1] != "spots" or parts[3] != "status":
        return None
    return parts[2]


def parse_mqtt_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_mqtt_status(value: str) -> SpotStatus:
    status = MQTT_STATUS_MAP.get(value.lower())
    if status is None:
        raise ValueError(f"Unsupported MQTT spot status: {value}")
    return status


def build_spot_event_request_from_mqtt(
    *,
    topic: str,
    payload: dict[str, Any],
) -> SpotEventRequest:
    topic_spot_id = spot_id_from_topic(topic)
    payload_spot_id = payload.get("spot_id")
    spot_id = payload_spot_id or topic_spot_id
    if not spot_id:
        raise ValueError("MQTT spot status event does not include spot_id.")
    if not isinstance(spot_id, str):
        raise ValueError("MQTT spot status event does not include string spot_id.")

    if topic_spot_id is not None and payload_spot_id is not None and topic_spot_id != payload_spot_id:
        raise ValueError(
            f"MQTT spot status topic spot_id '{topic_spot_id}' does not match payload spot_id '{payload_spot_id}'."
        )
    if not is_new_parking_spot_code(spot_id):
        raise ValueError(
            f"Unsupported MQTT spot_id format '{spot_id}'. Expected FLOOR-SECTOR-CAMERA_ZONE-SPOT, for example B1-A-02-1."
        )

    status = payload.get("status")
    if not isinstance(status, str):
        raise ValueError("MQTT spot status event does not include string status.")

    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, str):
        raise ValueError("MQTT spot status event does not include string timestamp.")

    event_id = f"{spot_id}:{status}:{timestamp}"
    parsed_sector_code = sector_code_from_spot_code(spot_id)
    parsed_camera_zone_code = camera_zone_code_from_spot_code(spot_id)
    payload_zone_id = payload.get("zone_id")
    sector_code = payload_zone_id or parsed_sector_code
    camera_zone_code = None
    if isinstance(payload_zone_id, str) and parsed_camera_zone_code == payload_zone_id:
        sector_code = parsed_sector_code
        camera_zone_code = parsed_camera_zone_code
    elif isinstance(payload_zone_id, str) and _looks_like_camera_zone_code(payload_zone_id):
        sector_code = _sector_code_from_camera_zone_code(payload_zone_id)
        camera_zone_code = payload_zone_id
    else:
        camera_zone_code = parsed_camera_zone_code

    return SpotEventRequest(
        spot_code=spot_id,
        sector_code=sector_code,
        camera_zone_code=camera_zone_code,
        status=normalize_mqtt_status(status),
        detected_at=parse_mqtt_timestamp(timestamp),
        source="MQTT",
        event_id=event_id,
        payload=payload,
    )


def ensure_mqtt_parking_config(
    db: Session,
    request: SpotEventRequest,
    *,
    create_missing_floor_sector: bool = False,
) -> bool:
    sector_code = request.sector_code
    if sector_code is None:
        raise ValueError("Cannot auto-create MQTT spot without sector_code.")

    created = False

    parsed = parse_parking_spot_code(request.spot_code)
    floor_code, sector_letter = _split_sector_code(sector_code)
    if create_missing_floor_sector:
        floor, floor_created = _ensure_floor(db, floor_code)
        sector, sector_created = _ensure_sector(db, floor, sector_code, sector_letter)
        created = created or floor_created or sector_created
    else:
        sector = _get_configured_sector(db, sector_code)

    camera_zone_code = request.camera_zone_code or camera_zone_code_from_spot_code(request.spot_code) or sector_code
    camera_zone_number = parsed.camera_zone_number if parsed is not None else camera_zone_code
    zone = db.scalar(select(ParkingZone).where(ParkingZone.code == camera_zone_code))
    if zone is None:
        zone = ParkingZone(
            sector_id=sector.id,
            title=f"Camera Zone {camera_zone_code}",
            code=camera_zone_code,
            zone_number=camera_zone_number or camera_zone_code,
            sort_order=_sort_order_from_spot_code(camera_zone_code),
            is_active=True,
        )
        db.add(zone)
        db.flush()
        created = True
    elif zone.sector_id != sector.id:
        zone.sector_id = sector.id
        created = True
    elif not zone.is_active:
        zone.is_active = True
        created = True

    spot = db.scalar(
        select(ParkingSpot).where(
            ParkingSpot.zone_id == zone.id,
            ParkingSpot.code == request.spot_code,
        )
    )
    if spot is None:
        spot = ParkingSpot(
            zone_id=zone.id,
            code=request.spot_code,
            status=SpotStatus.UNKNOWN.value,
            sort_order=_sort_order_from_spot_code(request.spot_code),
            is_active=True,
        )
        db.add(spot)
        created = True
    elif not spot.is_active:
        spot.is_active = True
        created = True

    if created:
        db.commit()

    return created


async def ensure_mqtt_parking_config_async(
    db: AsyncSession,
    request: SpotEventRequest,
    *,
    create_missing_floor_sector: bool = False,
) -> bool:
    sector_code = request.sector_code
    if sector_code is None:
        raise ValueError("Cannot auto-create MQTT spot without sector_code.")

    created = False

    parsed = parse_parking_spot_code(request.spot_code)
    floor_code, sector_letter = _split_sector_code(sector_code)
    if create_missing_floor_sector:
        floor, floor_created = await _ensure_floor_async(db, floor_code)
        sector, sector_created = await _ensure_sector_async(db, floor, sector_code, sector_letter)
        created = created or floor_created or sector_created
    else:
        sector = await _get_configured_sector_async(db, sector_code)

    camera_zone_code = request.camera_zone_code or camera_zone_code_from_spot_code(request.spot_code) or sector_code
    camera_zone_number = parsed.camera_zone_number if parsed is not None else camera_zone_code
    zone = await db.scalar(select(ParkingZone).where(ParkingZone.code == camera_zone_code))
    if zone is None:
        zone = ParkingZone(
            sector_id=sector.id,
            title=f"Camera Zone {camera_zone_code}",
            code=camera_zone_code,
            zone_number=camera_zone_number or camera_zone_code,
            sort_order=_sort_order_from_spot_code(camera_zone_code),
            is_active=True,
        )
        db.add(zone)
        await db.flush()
        created = True
    elif zone.sector_id != sector.id:
        zone.sector_id = sector.id
        created = True
    elif not zone.is_active:
        zone.is_active = True
        created = True

    spot = await db.scalar(
        select(ParkingSpot).where(
            ParkingSpot.zone_id == zone.id,
            ParkingSpot.code == request.spot_code,
        )
    )
    if spot is None:
        spot = ParkingSpot(
            zone_id=zone.id,
            code=request.spot_code,
            status=SpotStatus.UNKNOWN.value,
            sort_order=_sort_order_from_spot_code(request.spot_code),
            is_active=True,
        )
        db.add(spot)
        created = True
    elif not spot.is_active:
        spot.is_active = True
        created = True

    if created:
        await db.commit()

    return created


def _sort_order_from_spot_code(spot_code: str) -> int:
    digits = ""
    for char in reversed(spot_code):
        if not char.isdigit():
            break
        digits = char + digits
    return int(digits) if digits else 0


def _looks_like_camera_zone_code(value: str) -> bool:
    return len(value.split("-")) >= 3


def _sector_code_from_camera_zone_code(value: str) -> str:
    parts = value.split("-")
    return "-".join(parts[:2])


def _split_sector_code(sector_code: str) -> tuple[str, str]:
    if "-" not in sector_code:
        raise ValueError("Sector code must look like FLOOR-SECTOR, for example B1-A.")
    return tuple(sector_code.split("-", maxsplit=1))  # type: ignore[return-value]


def _configured_sector_error(sector_code: str) -> ValueError:
    return ValueError(
        f"Sector {sector_code} is not configured or inactive. "
        "Create it in admin before MQTT can auto-create camera zones and spots."
    )


def _get_configured_sector(db: Session, sector_code: str) -> ParkingSector:
    sector = db.scalar(
        select(ParkingSector)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.code == sector_code,
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
    )
    if sector is None:
        raise _configured_sector_error(sector_code)
    return sector


def _ensure_floor(db: Session, floor_code: str) -> tuple[ParkingFloor, bool]:
    floor = db.scalar(select(ParkingFloor).where(ParkingFloor.code == floor_code))
    if floor is not None:
        return floor, False
    floor = ParkingFloor(
        title=f"Floor {floor_code}",
        code=floor_code,
        sort_order=_sort_order_from_spot_code(floor_code),
        is_active=True,
    )
    db.add(floor)
    db.flush()
    return floor, True


def _ensure_sector(
    db: Session,
    floor: ParkingFloor,
    sector_code: str,
    sector_letter: str,
) -> tuple[ParkingSector, bool]:
    sector = db.scalar(select(ParkingSector).where(ParkingSector.code == sector_code))
    if sector is not None:
        return sector, False
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
    return sector, True


async def _ensure_floor_async(db: AsyncSession, floor_code: str) -> tuple[ParkingFloor, bool]:
    floor = await db.scalar(select(ParkingFloor).where(ParkingFloor.code == floor_code))
    if floor is not None:
        return floor, False
    floor = ParkingFloor(
        title=f"Floor {floor_code}",
        code=floor_code,
        sort_order=_sort_order_from_spot_code(floor_code),
        is_active=True,
    )
    db.add(floor)
    await db.flush()
    return floor, True


async def _get_configured_sector_async(db: AsyncSession, sector_code: str) -> ParkingSector:
    sector = await db.scalar(
        select(ParkingSector)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.code == sector_code,
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
    )
    if sector is None:
        raise _configured_sector_error(sector_code)
    return sector


async def _ensure_sector_async(
    db: AsyncSession,
    floor: ParkingFloor,
    sector_code: str,
    sector_letter: str,
) -> tuple[ParkingSector, bool]:
    sector = await db.scalar(select(ParkingSector).where(ParkingSector.code == sector_code))
    if sector is not None:
        return sector, False
    sector = ParkingSector(
        floor_id=floor.id,
        title=f"Sector {sector_code}",
        code=sector_code,
        sector_letter=sector_letter,
        sort_order=_sort_order_from_spot_code(sector_letter),
        is_active=True,
    )
    db.add(sector)
    await db.flush()
    return sector, True
