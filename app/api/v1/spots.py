from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.value_objects.spot_status import SpotStatus
from app.schemas.spots import SpotDetailResponse, SpotListResponse
from app.services.spots import get_spot_by_code, list_spots


router = APIRouter(tags=["spots"])


@router.get("/spots", response_model=SpotListResponse)
def get_spots(
    status: SpotStatus | None = None,
    zone_code: str | None = None,
    db: Session = Depends(get_db),
) -> SpotListResponse:
    return list_spots(
        db,
        status=status,
        zone_code=zone_code,
    )


@router.get("/spots/{spot_code}", response_model=SpotDetailResponse)
def get_spot(spot_code: str, db: Session = Depends(get_db)) -> SpotDetailResponse:
    spot = get_spot_by_code(db, spot_code)
    if spot is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Spot with code '{spot_code}' not found.",
        )

    return spot
