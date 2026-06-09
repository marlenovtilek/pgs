from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.led.factory import get_led_display_adapter
from app.core.async_database import get_async_db
from app.schemas.spot_event import SpotEventRequest, SpotEventResponse
from app.services.spot_events import AmbiguousSpotCodeError, process_spot_event_async


router = APIRouter(tags=["spot-events"])


@router.post(
    "/spot-events",
    response_model=SpotEventResponse,
    status_code=status.HTTP_200_OK,
)
async def create_spot_event(
    request: SpotEventRequest,
    db: AsyncSession = Depends(get_async_db),
) -> SpotEventResponse:
    try:
        result = await process_spot_event_async(
            db,
            request,
            display_port=get_led_display_adapter(),
        )
    except AmbiguousSpotCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Spot code '{exc.spot_code}' is ambiguous. "
                "Provide sector_code or camera_zone_code."
            ),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spot with code '{request.spot_code}' not found.",
        ) from exc

    return result.response
