from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_async_db
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_sector import ParkingSector
from app.schemas.display import (
    DisplayCreateRequest,
    DisplayItem,
    DisplayListResponse,
    DisplayListSummaryResponse,
    DisplayMessageListResponse,
    DisplayMessageResponse,
    DisplaySummaryResponse,
    DisplayUpdateRequest,
    EntryDisplayMessageResponse,
)
from app.services.display import (
    get_entry_display_message_async,
    get_display_message_async as build_display_message,
    get_display_summary_by_display_async,
    list_display_messages_async,
)

router = APIRouter(tags=["display"])


def _display_item_from_row(row) -> DisplayItem:
    return DisplayItem(
        zone_code=row.zone_code,
        display_code=row.display_code,
        display_title=row.display_title,
        arrow_direction=row.arrow_direction,
        is_active=row.is_active,
    )


@router.get(
    "/displays",
    response_model=DisplayListResponse,
)
async def get_displays(
    db: AsyncSession = Depends(get_async_db),
    zone_code: str | None = None,
    is_active: bool | None = None,
) -> DisplayListResponse:
    statement = (
        select(
            ParkingSector.code.label("zone_code"),
            GuidanceDisplay.code.label("display_code"),
            GuidanceDisplay.title.label("display_title"),
            GuidanceDisplay.arrow_direction,
            GuidanceDisplay.is_active,
        )
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .order_by(ParkingSector.code, GuidanceDisplay.code)
    )
    if zone_code is not None:
        statement = statement.where(ParkingSector.code == zone_code)
    if is_active is not None:
        statement = statement.where(GuidanceDisplay.is_active == is_active)

    rows = (await db.execute(statement)).all()
    return DisplayListResponse(items=[_display_item_from_row(row) for row in rows])


@router.get(
    "/displays/summary",
    response_model=DisplayListSummaryResponse,
)
async def get_displays_summary(
    db: AsyncSession = Depends(get_async_db),
    zone_code: str | None = None,
) -> DisplayListSummaryResponse:
    statement = (
        select(GuidanceDisplay, ParkingSector)
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .order_by(GuidanceDisplay.code)
    )
    if zone_code is not None:
        statement = statement.where(ParkingSector.code == zone_code)

    rows = (await db.execute(statement)).all()
    items = [
        await get_display_summary_by_display_async(db, display, zone)
        for display, zone in rows
    ]
    return DisplayListSummaryResponse(items=items)


@router.get(
    "/displays/messages",
    response_model=DisplayMessageListResponse,
)
async def get_displays_messages(
    db: AsyncSession = Depends(get_async_db),
    zone_code: str | None = None,
    is_active: bool | None = None,
) -> DisplayMessageListResponse:
    return DisplayMessageListResponse(
        items=await list_display_messages_async(
            db,
            zone_code=zone_code,
            is_active=is_active,
        )
    )


@router.get(
    "/displays/entry-message",
    response_model=EntryDisplayMessageResponse,
)
async def get_entry_display_message(
    db: AsyncSession = Depends(get_async_db),
    max_lines: int = 4,
) -> EntryDisplayMessageResponse:
    return await get_entry_display_message_async(db, max_lines=max_lines)


@router.post(
    "/displays",
    response_model=DisplayItem,
)
async def create_display(
    request: DisplayCreateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> DisplayItem:
    sector = await db.scalar(
        select(ParkingSector).where(ParkingSector.code == request.zone_code)
    )
    if sector is None:
        raise HTTPException(status_code=404, detail="Sector not found.")

    existing_display = await db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == request.code)
    )
    if existing_display is not None:
        raise HTTPException(status_code=400, detail="Display already exists.")

    display = GuidanceDisplay(
        title=request.title,
        code=request.code,
        sector_id=sector.id,
        arrow_direction=request.arrow_direction.value,
        is_active=request.is_active,
    )

    db.add(display)
    await db.commit()
    await db.refresh(display)

    return DisplayItem(
        zone_code=sector.code,
        display_code=display.code,
        display_title=display.title,
        arrow_direction=display.arrow_direction,
        is_active=display.is_active,
    )


@router.get(
    "/displays/{display_code}",
    response_model=DisplayItem,
)
async def get_display_by_code(
    display_code: str,
    db: AsyncSession = Depends(get_async_db),
) -> DisplayItem:
    statement = (
        select(
            ParkingSector.code.label("zone_code"),
            GuidanceDisplay.code.label("display_code"),
            GuidanceDisplay.title.label("display_title"),
            GuidanceDisplay.arrow_direction,
            GuidanceDisplay.is_active,
        )
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .where(GuidanceDisplay.code == display_code)
    )

    row = (await db.execute(statement)).first()

    if row is None:
        raise HTTPException(status_code=404, detail="Display not found.")

    return _display_item_from_row(row)


@router.get(
    "/displays/{display_code}/summary",
    response_model=DisplaySummaryResponse,
)
async def get_display_summary(
    display_code: str,
    db: AsyncSession = Depends(get_async_db),
) -> DisplaySummaryResponse:
    display = await db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == display_code)
    )
    if display is None:
        raise HTTPException(status_code=404, detail="Display not found.")

    sector = await db.scalar(select(ParkingSector).where(ParkingSector.id == display.sector_id))
    if sector is None:
        raise HTTPException(status_code=404, detail="Sector not found.")

    return await get_display_summary_by_display_async(db, display, sector)


@router.patch(
    "/displays/{display_code}",
    response_model=DisplayItem,
)
async def update_display(
    display_code: str,
    request: DisplayUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> DisplayItem:
    display = await db.scalar(
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

    await db.commit()
    await db.refresh(display)
    sector = await db.scalar(select(ParkingSector).where(ParkingSector.id == display.sector_id))
    if sector is None:
        raise HTTPException(status_code=404, detail="Sector not found.")

    return DisplayItem(
        zone_code=sector.code,
        display_code=display.code,
        display_title=display.title,
        arrow_direction=display.arrow_direction,
        is_active=display.is_active,
    )


@router.get(
    "/displays/{display_code}/message",
    response_model=DisplayMessageResponse,
)
async def get_display_message(
    display_code: str,
    db: AsyncSession = Depends(get_async_db),
) -> DisplayMessageResponse:
    message = await build_display_message(db, display_code)
    if message is None:
        raise HTTPException(status_code=404, detail="Display not found.")

    return message
