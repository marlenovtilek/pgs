from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_async_db
from app.domain.value_objects.spot_status import SpotStatus
from app.schemas.spots import SpotDetailResponse, SpotListResponse
from app.services.spots import (
    AmbiguousSpotCodeError,
    get_spot_by_code_async,
    list_spots_async,
)


router = APIRouter(tags=["spots"])


@router.get("/spots", response_model=SpotListResponse)
async def get_spots(
    status: SpotStatus | None = None,
    sector_code: str | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> SpotListResponse:
    return await list_spots_async(
        db,
        status=status,
        sector_code=sector_code,
    )


@router.get("/spots/{spot_code}", response_model=SpotDetailResponse)
async def get_spot(
    spot_code: str,
    sector_code: str | None = None,
    row_code: str | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> SpotDetailResponse:
    try:
        spot = await get_spot_by_code_async(
            db,
            spot_code,
            sector_code=sector_code,
            row_code=row_code,
        )
    except AmbiguousSpotCodeError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Spot code '{exc.spot_code}' is ambiguous. "
                "Provide sector_code or row_code."
            ),
        ) from exc

    if spot is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Spot with code '{spot_code}' not found.",
        )

    return spot
