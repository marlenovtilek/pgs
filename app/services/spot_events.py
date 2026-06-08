import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.ports.display import DisplayCommandPort
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.schemas.spot_event import SpotEventRequest, SpotEventResponse
from app.services.led import (
    publish_spot_display_messages,
    publish_spot_display_messages_async,
)
from app.services.spots import AmbiguousSpotCodeError, resolve_spot, resolve_spot_async


@dataclass(slots=True)
class SpotEventResult:
    response: SpotEventResponse
    is_duplicate: bool
    led_commands_sent: int


def build_dedup_key(
    *,
    spot_code: str,
    status_value: str,
    detected_at_iso: str,
    source: str,
    event_id: str | None,
) -> str:
    if event_id:
        return f"{source}:{event_id}"
    return f"{spot_code}:{status_value}:{detected_at_iso}:{source}"


def _duplicate_result(
    *,
    event: SpotOccupancyEvent,
    spot_code: str,
) -> SpotEventResult:
    return SpotEventResult(
        response=SpotEventResponse(
            success=True,
            dedup_key=event.dedup_key,
            spot_code=spot_code,
            status=event.status,
        ),
        is_duplicate=True,
        led_commands_sent=0,
    )


def process_spot_event(
    db: Session,
    request: SpotEventRequest,
    *,
    display_port: DisplayCommandPort | None = None,
) -> SpotEventResult:
    spot = resolve_spot(
        db,
        spot_code=request.spot_code,
        sector_code=request.sector_code,
        camera_zone_code=request.camera_zone_code,
    )
    if spot is None:
        raise LookupError(request.spot_code)
    spot_code = spot.code

    dedup_key = build_dedup_key(
        spot_code=spot_code,
        status_value=request.status.value,
        detected_at_iso=request.detected_at.isoformat(),
        source=request.source,
        event_id=request.event_id,
    )

    existing_event = db.scalar(
        select(SpotOccupancyEvent).where(SpotOccupancyEvent.dedup_key == dedup_key)
    )
    if existing_event is not None:
        return _duplicate_result(event=existing_event, spot_code=spot_code)

    event = SpotOccupancyEvent(
        spot_id=spot.id,
        event_id=request.event_id,
        dedup_key=dedup_key,
        status=request.status.value,
        source=request.source,
        payload=request.payload,
        detected_at=request.detected_at,
    )
    db.add(event)
    spot.status = request.status.value
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_event = db.scalar(
            select(SpotOccupancyEvent).where(SpotOccupancyEvent.dedup_key == dedup_key)
        )
        if existing_event is None:
            raise
        return _duplicate_result(event=existing_event, spot_code=spot_code)

    led_commands_sent = 0
    if display_port is not None:
        led_commands_sent = asyncio.run(
            publish_spot_display_messages(
                db,
                spot_id=spot.id,
                display_port=display_port,
            )
        )

    return SpotEventResult(
        response=SpotEventResponse(
            success=True,
            dedup_key=dedup_key,
            spot_code=spot_code,
            status=spot.status,
        ),
        is_duplicate=False,
        led_commands_sent=led_commands_sent,
    )


async def process_spot_event_async(
    db: AsyncSession,
    request: SpotEventRequest,
    *,
    display_port: DisplayCommandPort | None = None,
) -> SpotEventResult:
    spot = await resolve_spot_async(
        db,
        spot_code=request.spot_code,
        sector_code=request.sector_code,
        camera_zone_code=request.camera_zone_code,
    )
    if spot is None:
        raise LookupError(request.spot_code)
    spot_code = spot.code

    dedup_key = build_dedup_key(
        spot_code=spot_code,
        status_value=request.status.value,
        detected_at_iso=request.detected_at.isoformat(),
        source=request.source,
        event_id=request.event_id,
    )

    existing_event = await db.scalar(
        select(SpotOccupancyEvent).where(SpotOccupancyEvent.dedup_key == dedup_key)
    )
    if existing_event is not None:
        return _duplicate_result(event=existing_event, spot_code=spot_code)

    event = SpotOccupancyEvent(
        spot_id=spot.id,
        event_id=request.event_id,
        dedup_key=dedup_key,
        status=request.status.value,
        source=request.source,
        payload=request.payload,
        detected_at=request.detected_at,
    )
    db.add(event)
    spot.status = request.status.value
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_event = await db.scalar(
            select(SpotOccupancyEvent).where(SpotOccupancyEvent.dedup_key == dedup_key)
        )
        if existing_event is None:
            raise
        return _duplicate_result(event=existing_event, spot_code=spot_code)

    led_commands_sent = 0
    if display_port is not None:
        led_commands_sent = await publish_spot_display_messages_async(
            db,
            spot_id=spot.id,
            display_port=display_port,
        )

    return SpotEventResult(
        response=SpotEventResponse(
            success=True,
            dedup_key=dedup_key,
            spot_code=spot_code,
            status=spot.status,
        ),
        is_duplicate=False,
        led_commands_sent=led_commands_sent,
    )


__all__ = [
    "AmbiguousSpotCodeError",
    "SpotEventResult",
    "build_dedup_key",
    "process_spot_event",
    "process_spot_event_async",
]
