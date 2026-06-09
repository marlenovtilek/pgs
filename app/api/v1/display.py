from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_async_db
from app.models.guidance_display import GuidanceDisplay, guidance_display_zones
from app.models.led_device import LedDevice
from app.models.parking_sector import ParkingSector
from app.models.parking_zone import ParkingZone
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


async def _camera_zone_codes_for_display(
    db: AsyncSession,
    display_id: int,
) -> list[str]:
    rows = (
        await db.execute(
            select(ParkingZone.code)
            .join(guidance_display_zones, guidance_display_zones.c.zone_id == ParkingZone.id)
            .where(guidance_display_zones.c.display_id == display_id)
            .order_by(guidance_display_zones.c.sort_order, ParkingZone.code)
        )
    ).all()
    return [row.code for row in rows]


async def _display_item_from_display(
    db: AsyncSession,
    display: GuidanceDisplay,
    sector: ParkingSector,
) -> DisplayItem:
    led_device_code = None
    if display.led_device_id is not None:
        led_device_code = await db.scalar(
            select(LedDevice.code).where(LedDevice.id == display.led_device_id)
        )

    return DisplayItem(
        sector_code=sector.code,
        display_code=display.code,
        display_title=display.title,
        led_device_code=led_device_code,
        arrow_direction=display.arrow_direction,
        camera_zone_codes=await _camera_zone_codes_for_display(db, display.id),
        is_active=display.is_active,
    )


async def _camera_zone_ids_for_codes(
    db: AsyncSession,
    *,
    sector_id: int,
    camera_zone_codes: list[str],
) -> list[int]:
    unique_codes = list(dict.fromkeys(camera_zone_codes))
    if not unique_codes:
        return []

    rows = (
        await db.execute(
            select(ParkingZone.id, ParkingZone.code).where(
                ParkingZone.sector_id == sector_id,
                ParkingZone.code.in_(unique_codes),
            )
        )
    ).all()
    zone_ids_by_code = {row.code: row.id for row in rows}
    missing_codes = [code for code in unique_codes if code not in zone_ids_by_code]
    if missing_codes:
        raise HTTPException(
            status_code=404,
            detail=f"Camera zones not found in sector: {', '.join(missing_codes)}.",
        )

    return [zone_ids_by_code[code] for code in unique_codes]


async def _led_device_id_for_code(
    db: AsyncSession,
    led_device_code: str | None,
) -> int | None:
    if led_device_code is None:
        return None

    led_device_id = await db.scalar(
        select(LedDevice.id).where(LedDevice.code == led_device_code)
    )
    if led_device_id is None:
        raise HTTPException(status_code=404, detail="LED device not found.")
    return led_device_id


async def _replace_display_camera_zones(
    db: AsyncSession,
    *,
    display_id: int,
    zone_ids: list[int],
) -> None:
    await db.execute(
        delete(guidance_display_zones).where(guidance_display_zones.c.display_id == display_id)
    )
    for sort_order, zone_id in enumerate(zone_ids, start=1):
        await db.execute(
            guidance_display_zones.insert().values(
                display_id=display_id,
                zone_id=zone_id,
                sort_order=sort_order,
            )
        )


@router.get(
    "/displays",
    response_model=DisplayListResponse,
)
async def get_displays(
    db: AsyncSession = Depends(get_async_db),
    sector_code: str | None = None,
    is_active: bool | None = None,
) -> DisplayListResponse:
    statement = (
        select(GuidanceDisplay, ParkingSector)
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .order_by(ParkingSector.code, GuidanceDisplay.code)
    )
    if sector_code is not None:
        statement = statement.where(ParkingSector.code == sector_code)
    if is_active is not None:
        statement = statement.where(GuidanceDisplay.is_active == is_active)

    rows = (await db.execute(statement)).all()
    return DisplayListResponse(
        items=[
            await _display_item_from_display(db, display, sector)
            for display, sector in rows
        ]
    )


@router.get(
    "/displays/summary",
    response_model=DisplayListSummaryResponse,
)
async def get_displays_summary(
    db: AsyncSession = Depends(get_async_db),
    sector_code: str | None = None,
) -> DisplayListSummaryResponse:
    statement = (
        select(GuidanceDisplay, ParkingSector)
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .order_by(GuidanceDisplay.code)
    )
    if sector_code is not None:
        statement = statement.where(ParkingSector.code == sector_code)

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
    sector_code: str | None = None,
    is_active: bool | None = None,
) -> DisplayMessageListResponse:
    return DisplayMessageListResponse(
        items=await list_display_messages_async(
            db,
            sector_code=sector_code,
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
        select(ParkingSector).where(ParkingSector.code == request.sector_code)
    )
    if sector is None:
        raise HTTPException(status_code=404, detail="Sector not found.")

    existing_display = await db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == request.code)
    )
    if existing_display is not None:
        raise HTTPException(status_code=400, detail="Display already exists.")

    zone_ids = await _camera_zone_ids_for_codes(
        db,
        sector_id=sector.id,
        camera_zone_codes=request.camera_zone_codes,
    )

    display = GuidanceDisplay(
        title=request.title,
        code=request.code,
        sector_id=sector.id,
        led_device_id=await _led_device_id_for_code(db, request.led_device_code),
        arrow_direction=request.arrow_direction.value,
        is_active=request.is_active,
    )

    db.add(display)
    await db.flush()
    await _replace_display_camera_zones(db, display_id=display.id, zone_ids=zone_ids)
    await db.commit()
    await db.refresh(display)

    return await _display_item_from_display(db, display, sector)


@router.get(
    "/displays/{display_code}",
    response_model=DisplayItem,
)
async def get_display_by_code(
    display_code: str,
    db: AsyncSession = Depends(get_async_db),
) -> DisplayItem:
    statement = (
        select(GuidanceDisplay, ParkingSector)
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .where(GuidanceDisplay.code == display_code)
    )

    row = (await db.execute(statement)).first()

    if row is None:
        raise HTTPException(status_code=404, detail="Display not found.")

    display, sector = row
    return await _display_item_from_display(db, display, sector)


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

    if "led_device_code" in request.model_fields_set:
        display.led_device_id = await _led_device_id_for_code(db, request.led_device_code)

    if request.arrow_direction is not None:
        display.arrow_direction = request.arrow_direction.value

    if request.is_active is not None:
        display.is_active = request.is_active

    sector = await db.scalar(select(ParkingSector).where(ParkingSector.id == display.sector_id))
    if sector is None:
        raise HTTPException(status_code=404, detail="Sector not found.")

    if request.camera_zone_codes is not None:
        zone_ids = await _camera_zone_ids_for_codes(
            db,
            sector_id=sector.id,
            camera_zone_codes=request.camera_zone_codes,
        )
        await _replace_display_camera_zones(db, display_id=display.id, zone_ids=zone_ids)

    await db.commit()
    await db.refresh(display)

    return await _display_item_from_display(db, display, sector)


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
