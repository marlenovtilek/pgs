from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.ports.display import DisplayCommandPort
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.services.display import list_display_messages


def publish_zone_display_messages(
    db: Session,
    *,
    zone_id: int,
    display_port: DisplayCommandPort,
) -> int:
    zone_code = db.scalar(select(ParkingZone.code).where(ParkingZone.id == zone_id))
    if zone_code is None:
        return 0

    messages = list_display_messages(
        db,
        zone_code=zone_code,
        is_active=True,
    )

    for message in messages:
        display_port.show_zone_summary(
            display_code=message.display_code,
            zone_code=message.zone_code,
            free_spots=message.free_spots,
            arrow_direction=message.arrow_direction,
            message=message.message,
        )

    return len(messages)


def publish_spot_zone_display_messages(
    db: Session,
    *,
    spot_id: int,
    display_port: DisplayCommandPort,
) -> int:
    zone_id = db.scalar(
        select(ParkingRow.zone_id)
        .join(ParkingSpot, ParkingSpot.row_id == ParkingRow.id)
        .where(ParkingSpot.id == spot_id)
    )
    if zone_id is None:
        return 0

    return publish_zone_display_messages(
        db,
        zone_id=zone_id,
        display_port=display_port,
    )
