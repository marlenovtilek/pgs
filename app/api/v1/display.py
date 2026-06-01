from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.parking_zone import ParkingZone
from app.models.guidance_display import GuidanceDisplay
from app.schemas.display import DisplayCreateRequest, DisplayItem, DisplayListResponse, DisplayMessageListResponse, DisplayMessageResponse, DisplaySummaryResponse, DisplayListSummaryResponse, DisplayUpdateRequest
from app.services.display import (
    get_display_message as build_display_message,
    get_display_summary_by_display,
    list_display_messages,
)

router = APIRouter(tags=["display"])

@router.get(
    "/displays",
    response_model=DisplayListResponse,
)
def get_displays(
    db: Session = Depends(get_db),
    zone_code: str | None = None,
    is_active: bool | None = None,
    ) -> DisplayListResponse:
    statement = (
        select(
            ParkingZone.code.label("zone_code"),
            GuidanceDisplay.code.label("display_code"),
            GuidanceDisplay.title.label("display_title"),
            GuidanceDisplay.arrow_direction,
            GuidanceDisplay.is_active,
        )
        .join(ParkingZone, GuidanceDisplay.zone_id == ParkingZone.id)
        .order_by(ParkingZone.code, GuidanceDisplay.code)
    )
    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)
    if is_active is not None:
        statement = statement.where(GuidanceDisplay.is_active == is_active)
    rows = db.execute(statement).all()
    items = [
        DisplayItem(
            zone_code=row.zone_code,
            display_code=row.display_code,
            display_title=row.display_title,
            arrow_direction=row.arrow_direction,
            is_active=row.is_active
        )
        for row in rows
    ]
    return DisplayListResponse(items=items)


@router.get(
    "/displays/summary",
    response_model=DisplayListSummaryResponse,
)
def get_displays_summary(
    db: Session = Depends(get_db),
    zone_code: str | None = None,
    ) -> DisplayListSummaryResponse:
    displays = db.scalars(
        select(GuidanceDisplay).order_by(GuidanceDisplay.code)
    ).all()
    items = []
    for display in displays:

        zone = db.scalar(
            select(ParkingZone).where(ParkingZone.id == display.zone_id)
        )
        if zone is None:
            continue
        if zone_code is not None and zone.code != zone_code:
            continue
        rows = db.execute(
            select(
                ParkingSpot.status
            )
            .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
            .where(ParkingRow.zone_id == display.zone_id)
        ).all()
        statuses = [SpotStatus(row.status) for row in rows]

        summary = calculate_zone_summary(statuses)

        items.append(
            DisplaySummaryResponse(
                display_code=display.code,
                display_title=display.title,
                zone_code=zone.code,
                arrow_direction=display.arrow_direction,
                total_spots=summary["total"],
                free_spots=summary["free"],
                occupied_spots=summary["occupied"],
            )
        )
    return DisplayListSummaryResponse(items=items)


@router.get(
    "/displays/messages",
    response_model=DisplayMessageListResponse,
)
def get_displays_messages(
    db: Session = Depends(get_db),
    zone_code: str | None = None,
    is_active: bool | None = None,
) -> DisplayMessageListResponse:
    return DisplayMessageListResponse(
        items=list_display_messages(
            db,
            zone_code=zone_code,
            is_active=is_active,
        )
    )


@router.post(
    "/displays",
    response_model=DisplayItem,
)
def create_display(
    request: DisplayCreateRequest,
    db: Session = Depends(get_db),
) -> DisplayItem:
    zone = db.scalar(
        select(ParkingZone).where(ParkingZone.code == request.zone_code)
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found.")

    existing_display = db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == request.code)
    )
    if existing_display is not None:
        raise HTTPException(status_code=400, detail="Display already exists.")

    display = GuidanceDisplay(
        title=request.title,
        code=request.code,
        zone_id=zone.id,
        arrow_direction=request.arrow_direction.value,
        is_active=request.is_active,
    )

    db.add(display)
    db.commit()
    db.refresh(display)

    return DisplayItem(
        zone_code=zone.code,
        display_code=display.code,
        display_title=display.title,
        arrow_direction=display.arrow_direction,
        is_active=display.is_active,
    )


@router.get(
    "/displays/{display_code}",
    response_model=DisplayItem,
)
def get_display_by_code(
    display_code: str,
    db: Session = Depends(get_db),
) -> DisplayItem:
    statement = (
        select(
            ParkingZone.code.label("zone_code"),
            GuidanceDisplay.code.label("display_code"),
            GuidanceDisplay.title.label("display_title"),
            GuidanceDisplay.arrow_direction,
            GuidanceDisplay.is_active,
        )
        .join(ParkingZone, GuidanceDisplay.zone_id == ParkingZone.id)
        .where(GuidanceDisplay.code == display_code)
    )

    row = db.execute(statement).first()

    if row is None:
        raise HTTPException(status_code=404, detail="Display not found.")

    return DisplayItem(
        zone_code=row.zone_code,
        display_code=row.display_code,
        display_title=row.display_title,
        arrow_direction=row.arrow_direction,
        is_active=row.is_active,
    )


@router.get(
    "/displays/{display_code}/summary",
    response_model=DisplaySummaryResponse,
)
def get_display_summary(
    display_code: str,
    db: Session = Depends(get_db),
) -> DisplaySummaryResponse:
    display = db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == display_code)
    )
    if display is None:
        raise HTTPException(status_code=404, detail="Display not found.")

    zone = db.scalar(
        select(ParkingZone).where(ParkingZone.id == display.zone_id)
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found.")

    return get_display_summary_by_display(db, display, zone)


@router.patch(
    "/displays/{display_code}",
    response_model=DisplayItem,
)
def update_display(
    display_code: str,
    request: DisplayUpdateRequest,
    db: Session = Depends(get_db),
) -> DisplayItem:
    display = db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == display_code)
    )
    if display is None:
        raise HTTPException(status_code=404, detail="Display not found.")
    
    if request.title is not None:
        display.title = request.title
    
    if request.arrow_direction is not None:
        display.arrow_direction = request.arrow_direction.value

    if request.is_active is not None:
        display.is_active = request.is_active
    
    db.commit()
    db.refresh(display)
    zone = db.scalar(
        select(ParkingZone).where(ParkingZone.id == display.zone_id)
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found.")
    
    return DisplayItem(
        zone_code=zone.code,
        display_code=display.code,
        display_title=display.title,
        arrow_direction=display.arrow_direction,
        is_active=display.is_active,
    )


@router.get(
    "/displays/{display_code}/message",
    response_model=DisplayMessageResponse,
)
def get_display_message(
    display_code: str,
    db: Session = Depends(get_db),
) -> DisplayMessageResponse:
    message = build_display_message(db, display_code)
    if message is None:
        raise HTTPException(status_code=404, detail="Display not found.")

    return message
