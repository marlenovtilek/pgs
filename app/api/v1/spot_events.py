from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.led.mock import mock_led_adapter
from app.core.database import get_db
from app.schemas.spot_event import SpotEventRequest, SpotEventResponse
from app.services.spot_events import AmbiguousSpotCodeError, process_spot_event


router = APIRouter(tags=["spot-events"])


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
        result = process_spot_event(
            db,
            request,
            display_port=mock_led_adapter,
        )
    except AmbiguousSpotCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Spot code '{exc.spot_code}' is ambiguous. "
                "Provide zone_code or row_code."
            ),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spot with code '{request.spot_code}' not found.",
        ) from exc

    return result.response
