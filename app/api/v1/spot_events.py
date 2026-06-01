from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.schemas.spot_event import SpotEventRequest, SpotEventResponse
from app.services.spots import AmbiguousSpotCodeError, resolve_spot


router = APIRouter(tags=["spot-events"])


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


@router.post(
    "/spot-events",
    response_model=SpotEventResponse,
    status_code=status.HTTP_200_OK,
)
def create_spot_event(
    request: SpotEventRequest,
    db: Session = Depends(get_db),
) -> SpotEventResponse:
    try:
        spot = resolve_spot(
            db,
            spot_code=request.spot_code,
            zone_code=request.zone_code,
            row_code=request.row_code,
        )
    except AmbiguousSpotCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Spot code '{exc.spot_code}' is ambiguous. "
                "Provide zone_code or row_code."
            ),
        ) from exc

    if spot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spot with code '{request.spot_code}' not found.",
        )

    dedup_key = build_dedup_key(
        spot_code=spot.code,
        status_value=request.status.value,
        detected_at_iso=request.detected_at.isoformat(),
        source=request.source,
        event_id=request.event_id,
    )

    existing_event = db.scalar(
        select(SpotOccupancyEvent).where(SpotOccupancyEvent.dedup_key == dedup_key)
    )
    if existing_event is not None:
        return SpotEventResponse(
            success=True,
            dedup_key=existing_event.dedup_key,
            spot_code=spot.code,
            status=existing_event.status,
        )

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
    db.commit()

    return SpotEventResponse(
        success=True,
        dedup_key=dedup_key,
        spot_code=spot.code,
        status=spot.status,
    )
