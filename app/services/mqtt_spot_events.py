import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
from app.services.parking_structure import (
    get_or_create_floor,
    get_or_create_floor_async,
    get_or_create_sector,
    get_or_create_sector_async,
    sort_order_from_code,
    split_sector_code,
)


logger = logging.getLogger(__name__)


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


def _camera_zone_fields(
    request: SpotEventRequest,
    parsed,
    sector_code: str,
) -> tuple[str, str]:
    code = (
        request.camera_zone_code
        or camera_zone_code_from_spot_code(request.spot_code)
        or sector_code
    )
    number = parsed.camera_zone_number if parsed is not None else code
    return code, (number or code)


def _build_camera_zone(sector_id: int, code: str, number: str) -> ParkingZone:
    return ParkingZone(
        sector_id=sector_id,
        title=f"Camera Zone {code}",
        code=code,
        zone_number=number,
        sort_order=sort_order_from_code(code),
        is_active=True,
    )


def _build_spot(zone_id: int, spot_code: str) -> ParkingSpot:
    return ParkingSpot(
        zone_id=zone_id,
        code=spot_code,
        status=SpotStatus.UNKNOWN.value,
        sort_order=sort_order_from_code(spot_code),
        is_active=True,
    )


def _reconcile_camera_zone(zone: ParkingZone, sector_id: int) -> bool:
    if zone.sector_id != sector_id:
        logger.warning(
            "camera_zone_reassigned code=%s from_sector_id=%s to_sector_id=%s",
            zone.code,
            zone.sector_id,
            sector_id,
        )
        zone.sector_id = sector_id
        return True
    if not zone.is_active:
        zone.is_active = True
        return True
    return False


def _reconcile_spot(spot: ParkingSpot) -> bool:
    if not spot.is_active:
        spot.is_active = True
        return True
    return False


def ensure_mqtt_parking_config(
    db: Session,
    request: SpotEventRequest,
    *,
    create_missing_floor_sector: bool = False,
) -> bool:
    try:
        return _ensure_mqtt_parking_config(
            db, request, create_missing_floor_sector=create_missing_floor_sector
        )
    except IntegrityError:
        db.rollback()
        logger.warning(
            "auto_create_race spot_code=%s, retrying after rollback",
            request.spot_code,
        )
        return _ensure_mqtt_parking_config(
            db, request, create_missing_floor_sector=create_missing_floor_sector
        )


def _ensure_mqtt_parking_config(
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
    floor_code, sector_letter = split_sector_code(sector_code)
    if create_missing_floor_sector:
        floor, floor_created = get_or_create_floor(db, floor_code)
        sector, sector_created = get_or_create_sector(db, floor, sector_code, sector_letter)
        created = created or floor_created or sector_created
    else:
        sector = _get_configured_sector(db, sector_code)

    camera_zone_code, camera_zone_number = _camera_zone_fields(request, parsed, sector_code)
    zone = db.scalar(select(ParkingZone).where(ParkingZone.code == camera_zone_code))
    if zone is None:
        zone = _build_camera_zone(sector.id, camera_zone_code, camera_zone_number)
        db.add(zone)
        db.flush()
        created = True
    elif _reconcile_camera_zone(zone, sector.id):
        created = True

    spot = db.scalar(
        select(ParkingSpot).where(
            ParkingSpot.zone_id == zone.id,
            ParkingSpot.code == request.spot_code,
        )
    )
    if spot is None:
        db.add(_build_spot(zone.id, request.spot_code))
        created = True
    elif _reconcile_spot(spot):
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
    try:
        return await _ensure_mqtt_parking_config_async(
            db, request, create_missing_floor_sector=create_missing_floor_sector
        )
    except IntegrityError:
        await db.rollback()
        logger.warning(
            "auto_create_race spot_code=%s, retrying after rollback",
            request.spot_code,
        )
        return await _ensure_mqtt_parking_config_async(
            db, request, create_missing_floor_sector=create_missing_floor_sector
        )


async def _ensure_mqtt_parking_config_async(
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
    floor_code, sector_letter = split_sector_code(sector_code)
    if create_missing_floor_sector:
        floor, floor_created = await get_or_create_floor_async(db, floor_code)
        sector, sector_created = await get_or_create_sector_async(db, floor, sector_code, sector_letter)
        created = created or floor_created or sector_created
    else:
        sector = await _get_configured_sector_async(db, sector_code)

    camera_zone_code, camera_zone_number = _camera_zone_fields(request, parsed, sector_code)
    zone = await db.scalar(select(ParkingZone).where(ParkingZone.code == camera_zone_code))
    if zone is None:
        zone = _build_camera_zone(sector.id, camera_zone_code, camera_zone_number)
        db.add(zone)
        await db.flush()
        created = True
    elif _reconcile_camera_zone(zone, sector.id):
        created = True

    spot = await db.scalar(
        select(ParkingSpot).where(
            ParkingSpot.zone_id == zone.id,
            ParkingSpot.code == request.spot_code,
        )
    )
    if spot is None:
        db.add(_build_spot(zone.id, request.spot_code))
        created = True
    elif _reconcile_spot(spot):
        created = True

    if created:
        await db.commit()

    return created


def _looks_like_camera_zone_code(value: str) -> bool:
    return len(value.split("-")) >= 3


def _sector_code_from_camera_zone_code(value: str) -> str:
    parts = value.split("-")
    return "-".join(parts[:2])


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

