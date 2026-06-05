import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.use_cases import calculate_zone_summary
from app.domain.value_objects.arrow_direction import resolve_display_arrow_direction
from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.display import (
    DisplayMessageResponse,
    DisplaySummaryResponse,
    EntryDisplayMessageResponse,
)


FLOOR_SECTOR_ZONE_CODE_PATTERN = re.compile(r"^[A-Za-z]\d+-[A-Za-z]+$")
PARKING_SYMBOL = "P"


def _sector_statuses(db: Session, sector_id: int) -> list[SpotStatus]:
    rows = db.execute(
        select(ParkingSpot.status)
        .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
        .where(
            ParkingZone.sector_id == sector_id,
            ParkingZone.is_active.is_(True),
            ParkingSpot.is_active.is_(True),
        )
    ).all()

    return [SpotStatus(row.status) for row in rows]


async def _sector_statuses_async(db: AsyncSession, sector_id: int) -> list[SpotStatus]:
    rows = (
        await db.execute(
            select(ParkingSpot.status)
            .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
            .where(
                ParkingZone.sector_id == sector_id,
                ParkingZone.is_active.is_(True),
                ParkingSpot.is_active.is_(True),
            )
        )
    ).all()

    return [SpotStatus(row.status) for row in rows]


def _build_display_message(
    *,
    display: GuidanceDisplay,
    sector: ParkingSector,
    free_spots: int,
) -> DisplayMessageResponse:
    arrow_direction = resolve_display_arrow_direction(
        display.arrow_direction,
        free_spots,
    ).value
    message = _format_display_message(
        sector_code=sector.code,
        arrow_direction=arrow_direction,
        free_spots=free_spots,
    )
    display_text = _format_small_led_display_text(
        arrow_direction=arrow_direction,
        free_spots=free_spots,
    )

    return DisplayMessageResponse(
        display_code=display.code,
        sector_code=sector.code,
        arrow_direction=arrow_direction,
        free_spots=free_spots,
        parking_symbol=PARKING_SYMBOL,
        display_text=display_text,
        message=message,
    )


def _format_small_led_display_text(
    *,
    arrow_direction: str,
    free_spots: int,
) -> str:
    return f"{arrow_direction} {free_spots} {PARKING_SYMBOL}"


def _format_display_message(
    *,
    sector_code: str,
    arrow_direction: str,
    free_spots: int,
) -> str:
    if FLOOR_SECTOR_ZONE_CODE_PATTERN.match(sector_code) is None:
        return f"{sector_code} {arrow_direction} {free_spots}"

    return f"{sector_code} {free_spots}"


def build_entry_display_message(
    messages: list[DisplayMessageResponse],
    *,
    display_code: str = "DISP-ENTRY-MAIN",
    title: str = "Entry Main Display",
    max_lines: int = 4,
) -> EntryDisplayMessageResponse:
    sorted_messages = sorted(messages, key=lambda message: message.sector_code)
    lines = [message.message for message in sorted_messages[:max_lines]]
    free_spots = sum(message.free_spots for message in sorted_messages)

    return EntryDisplayMessageResponse(
        display_code=display_code,
        title=title,
        lines=lines,
        free_spots=free_spots,
        message=" | ".join(lines),
    )


def get_display_summary_by_display(
    db: Session,
    display: GuidanceDisplay,
    sector: ParkingSector,
) -> DisplaySummaryResponse:
    summary = calculate_zone_summary(_sector_statuses(db, sector.id))

    return DisplaySummaryResponse(
        display_code=display.code,
        display_title=display.title,
        sector_code=sector.code,
        arrow_direction=display.arrow_direction,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
    )


async def get_display_summary_by_display_async(
    db: AsyncSession,
    display: GuidanceDisplay,
    sector: ParkingSector,
) -> DisplaySummaryResponse:
    summary = calculate_zone_summary(await _sector_statuses_async(db, sector.id))

    return DisplaySummaryResponse(
        display_code=display.code,
        display_title=display.title,
        sector_code=sector.code,
        arrow_direction=display.arrow_direction,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
    )


def get_display_message_by_display(
    db: Session,
    display: GuidanceDisplay,
    sector: ParkingSector,
) -> DisplayMessageResponse:
    summary = calculate_zone_summary(_sector_statuses(db, sector.id))

    return _build_display_message(
        display=display,
        sector=sector,
        free_spots=summary["free"],
    )


async def get_display_message_by_display_async(
    db: AsyncSession,
    display: GuidanceDisplay,
    sector: ParkingSector,
) -> DisplayMessageResponse:
    summary = calculate_zone_summary(await _sector_statuses_async(db, sector.id))

    return _build_display_message(
        display=display,
        sector=sector,
        free_spots=summary["free"],
    )


def get_display_message(
    db: Session,
    display_code: str,
) -> DisplayMessageResponse | None:
    display = db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == display_code)
    )
    if display is None:
        return None

    sector = db.scalar(
        select(ParkingSector)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.id == display.sector_id,
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
    )
    if sector is None:
        return None

    return get_display_message_by_display(db, display, sector)


async def get_display_message_async(
    db: AsyncSession,
    display_code: str,
) -> DisplayMessageResponse | None:
    display = await db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == display_code)
    )
    if display is None:
        return None

    sector = await db.scalar(
        select(ParkingSector)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.id == display.sector_id,
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
    )
    if sector is None:
        return None

    return await get_display_message_by_display_async(db, display, sector)


def list_display_messages(
    db: Session,
    *,
    sector_code: str | None = None,
    is_active: bool | None = None,
) -> list[DisplayMessageResponse]:
    statement = (
        select(GuidanceDisplay, ParkingSector)
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
        .order_by(GuidanceDisplay.code)
    )

    if sector_code is not None:
        statement = statement.where(ParkingSector.code == sector_code)

    if is_active is not None:
        statement = statement.where(GuidanceDisplay.is_active == is_active)

    rows = db.execute(statement).all()

    return [
        get_display_message_by_display(db, display, zone)
        for display, zone in rows
    ]


async def list_display_messages_async(
    db: AsyncSession,
    *,
    sector_code: str | None = None,
    is_active: bool | None = None,
) -> list[DisplayMessageResponse]:
    statement = (
        select(GuidanceDisplay, ParkingSector)
        .join(ParkingSector, GuidanceDisplay.sector_id == ParkingSector.id)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
        .order_by(GuidanceDisplay.code)
    )

    if sector_code is not None:
        statement = statement.where(ParkingSector.code == sector_code)

    if is_active is not None:
        statement = statement.where(GuidanceDisplay.is_active == is_active)

    rows = (await db.execute(statement)).all()

    return [
        await get_display_message_by_display_async(db, display, zone)
        for display, zone in rows
    ]


async def get_entry_display_message_async(
    db: AsyncSession,
    *,
    max_lines: int = 4,
) -> EntryDisplayMessageResponse:
    messages = await list_display_messages_async(db, is_active=True)
    return build_entry_display_message(messages, max_lines=max_lines)
