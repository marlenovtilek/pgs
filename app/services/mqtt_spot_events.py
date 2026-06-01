from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.value_objects.spot_status import SpotStatus
from app.domain.value_objects.arrow_direction import ArrowDirection
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.spot_event import SpotEventRequest


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

    if topic_spot_id is not None and payload_spot_id is not None and topic_spot_id != payload_spot_id:
        raise ValueError(
            f"MQTT spot status topic spot_id '{topic_spot_id}' does not match payload spot_id '{payload_spot_id}'."
        )

    status = payload.get("status")
    if not isinstance(status, str):
        raise ValueError("MQTT spot status event does not include string status.")

    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, str):
        raise ValueError("MQTT spot status event does not include string timestamp.")

    event_id = f"{spot_id}:{status}:{timestamp}"

    return SpotEventRequest(
        spot_code=spot_id,
        zone_code=payload.get("zone_id"),
        status=normalize_mqtt_status(status),
        detected_at=parse_mqtt_timestamp(timestamp),
        source="MQTT",
        event_id=event_id,
        payload=payload,
    )


def ensure_mqtt_parking_config(db: Session, request: SpotEventRequest) -> bool:
    zone_code = request.zone_code
    if zone_code is None:
        raise ValueError("Cannot auto-create MQTT spot without zone_code.")

    created = False

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
        created = True

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
        created = True

    spot = db.scalar(
        select(ParkingSpot).where(
            ParkingSpot.row_id == row.id,
            ParkingSpot.code == request.spot_code,
        )
    )
    if spot is None:
        spot = ParkingSpot(
            row_id=row.id,
            code=request.spot_code,
            status=SpotStatus.UNKNOWN.value,
            sort_order=_sort_order_from_spot_code(request.spot_code),
            is_active=True,
        )
        db.add(spot)
        created = True

    display_code = f"DISP-{zone_code}"
    display = db.scalar(select(GuidanceDisplay).where(GuidanceDisplay.code == display_code))
    if display is None:
        display = GuidanceDisplay(
            title=f"Display {zone_code}",
            code=display_code,
            zone_id=zone.id,
            arrow_direction=ArrowDirection.AHEAD.value,
            is_active=True,
        )
        db.add(display)
        created = True

    if created:
        db.commit()

    return created


def _sort_order_from_spot_code(spot_code: str) -> int:
    digits = ""
    for char in reversed(spot_code):
        if not char.isdigit():
            break
        digits = char + digits
    return int(digits) if digits else 0
