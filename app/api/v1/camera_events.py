from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.guidance_camera import GuidanceCamera
from app.models.parking_spot import ParkingSpot
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.schemas.camera_event import (
    SimulateCameraEventRequest,
    SimulateCameraEventResponse,
)


router = APIRouter(tags=["camera-events"])


def build_dedup_key(
    camera_code: str,
    spot_code: str,
    status_value: str,
    detected_at_iso: str,
) -> str:
    return f"{camera_code}:{spot_code}:{status_value}:{detected_at_iso}"


@router.post(
    "/simulate/camera-event",
    response_model=SimulateCameraEventResponse,
    status_code=status.HTTP_200_OK,
)
def simulate_camera_event(
    request: SimulateCameraEventRequest,
    db: Session = Depends(get_db),
) -> SimulateCameraEventResponse:
    camera = db.scalar(
        select(GuidanceCamera).where(GuidanceCamera.code == request.camera_code)
    )
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with code '{request.camera_code}' not found.",
        )

    spot = db.scalar(select(ParkingSpot).where(ParkingSpot.code == request.spot_code))
    if spot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spot with code '{request.spot_code}' not found.",
        )

    dedup_key = build_dedup_key(
        camera_code=camera.code,
        spot_code=spot.code,
        status_value=request.status.value,
        detected_at_iso=request.detected_at.isoformat(),
    )

    existing_event = db.scalar(
        select(SpotOccupancyEvent).where(SpotOccupancyEvent.dedup_key == dedup_key)
    )
    if existing_event is not None:
        return SimulateCameraEventResponse(
            success=True,
            dedup_key=existing_event.dedup_key,
            spot_code=spot.code,
            status=existing_event.status,
        )

    event = SpotOccupancyEvent(
        camera_id=camera.id,
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

    return SimulateCameraEventResponse(
        success=True,
        dedup_key=dedup_key,
        spot_code=spot.code,
        status=spot.status,
    )
