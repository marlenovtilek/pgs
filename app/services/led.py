from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.ports.display import DisplayCommandPort
from app.models.parking_spot import ParkingSpot
from app.models.parking_sector import ParkingSector
from app.models.parking_zone import ParkingZone
from app.services.display import list_display_messages, list_display_messages_async


async def publish_zone_display_messages(
    db: Session,
    *,
    zone_id: int,
    display_port: DisplayCommandPort,
) -> int:
    zone_code = db.scalar(select(ParkingSector.code).where(ParkingSector.id == zone_id))
    if zone_code is None:
        return 0

    messages = list_display_messages(
        db,
        zone_code=zone_code,
        is_active=True,
    )

    for message in messages:
        await display_port.show_zone_summary(
            display_code=message.display_code,
            zone_code=message.zone_code,
            free_spots=message.free_spots,
            arrow_direction=message.arrow_direction,
            parking_symbol=message.parking_symbol,
            display_text=message.display_text,
            message=message.message,
        )

    return len(messages)


async def publish_spot_zone_display_messages(
    db: Session,
    *,
    spot_id: int,
    display_port: DisplayCommandPort,
) -> int:
    zone_id = db.scalar(
        select(ParkingZone.sector_id)
        .join(ParkingSpot, ParkingSpot.zone_id == ParkingZone.id)
        .where(ParkingSpot.id == spot_id)
    )
    if zone_id is None:
        return 0

    return await publish_zone_display_messages(
        db,
        zone_id=zone_id,
        display_port=display_port,
    )


async def publish_zone_display_messages_async(
    db: AsyncSession,
    *,
    zone_id: int,
    display_port: DisplayCommandPort,
) -> int:
    zone_code = await db.scalar(select(ParkingSector.code).where(ParkingSector.id == zone_id))
    if zone_code is None:
        return 0

    messages = await list_display_messages_async(
        db,
        zone_code=zone_code,
        is_active=True,
    )

    for message in messages:
        await display_port.show_zone_summary(
            display_code=message.display_code,
            zone_code=message.zone_code,
            free_spots=message.free_spots,
            arrow_direction=message.arrow_direction,
            parking_symbol=message.parking_symbol,
            display_text=message.display_text,
            message=message.message,
        )

    return len(messages)


async def publish_spot_zone_display_messages_async(
    db: AsyncSession,
    *,
    spot_id: int,
    display_port: DisplayCommandPort,
) -> int:
    zone_id = await db.scalar(
        select(ParkingZone.sector_id)
        .join(ParkingSpot, ParkingSpot.zone_id == ParkingZone.id)
        .where(ParkingSpot.id == spot_id)
    )
    if zone_id is None:
        return 0

    return await publish_zone_display_messages_async(
        db,
        zone_id=zone_id,
        display_port=display_port,
    )
