from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.use_cases import calculate_zone_summary
from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.display import DisplayMessageResponse, DisplaySummaryResponse


def _zone_statuses(db: Session, zone_id: int) -> list[SpotStatus]:
    rows = db.execute(
        select(ParkingSpot.status)
        .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
        .where(ParkingRow.zone_id == zone_id)
    ).all()

    return [SpotStatus(row.status) for row in rows]


async def _zone_statuses_async(db: AsyncSession, zone_id: int) -> list[SpotStatus]:
    rows = (
        await db.execute(
            select(ParkingSpot.status)
            .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
            .where(ParkingRow.zone_id == zone_id)
        )
    ).all()

    return [SpotStatus(row.status) for row in rows]


def _build_display_message(
    *,
    display: GuidanceDisplay,
    zone: ParkingZone,
    free_spots: int,
) -> DisplayMessageResponse:
    arrow_direction = "FULL" if free_spots == 0 else display.arrow_direction

    return DisplayMessageResponse(
        display_code=display.code,
        zone_code=zone.code,
        arrow_direction=arrow_direction,
        free_spots=free_spots,
        message=f"{zone.code} {arrow_direction} {free_spots}",
    )


def get_display_summary_by_display(
    db: Session,
    display: GuidanceDisplay,
    zone: ParkingZone,
) -> DisplaySummaryResponse:
    summary = calculate_zone_summary(_zone_statuses(db, zone.id))

    return DisplaySummaryResponse(
        display_code=display.code,
        display_title=display.title,
        zone_code=zone.code,
        arrow_direction=display.arrow_direction,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
    )


async def get_display_summary_by_display_async(
    db: AsyncSession,
    display: GuidanceDisplay,
    zone: ParkingZone,
) -> DisplaySummaryResponse:
    summary = calculate_zone_summary(await _zone_statuses_async(db, zone.id))

    return DisplaySummaryResponse(
        display_code=display.code,
        display_title=display.title,
        zone_code=zone.code,
        arrow_direction=display.arrow_direction,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
    )


def get_display_message_by_display(
    db: Session,
    display: GuidanceDisplay,
    zone: ParkingZone,
) -> DisplayMessageResponse:
    summary = calculate_zone_summary(_zone_statuses(db, zone.id))

    return _build_display_message(
        display=display,
        zone=zone,
        free_spots=summary["free"],
    )


async def get_display_message_by_display_async(
    db: AsyncSession,
    display: GuidanceDisplay,
    zone: ParkingZone,
) -> DisplayMessageResponse:
    summary = calculate_zone_summary(await _zone_statuses_async(db, zone.id))

    return _build_display_message(
        display=display,
        zone=zone,
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

    zone = db.scalar(select(ParkingZone).where(ParkingZone.id == display.zone_id))
    if zone is None:
        return None

    return get_display_message_by_display(db, display, zone)


async def get_display_message_async(
    db: AsyncSession,
    display_code: str,
) -> DisplayMessageResponse | None:
    display = await db.scalar(
        select(GuidanceDisplay).where(GuidanceDisplay.code == display_code)
    )
    if display is None:
        return None

    zone = await db.scalar(select(ParkingZone).where(ParkingZone.id == display.zone_id))
    if zone is None:
        return None

    return await get_display_message_by_display_async(db, display, zone)


def list_display_messages(
    db: Session,
    *,
    zone_code: str | None = None,
    is_active: bool | None = None,
) -> list[DisplayMessageResponse]:
    statement = (
        select(GuidanceDisplay, ParkingZone)
        .join(ParkingZone, GuidanceDisplay.zone_id == ParkingZone.id)
        .order_by(GuidanceDisplay.code)
    )

    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)

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
    zone_code: str | None = None,
    is_active: bool | None = None,
) -> list[DisplayMessageResponse]:
    statement = (
        select(GuidanceDisplay, ParkingZone)
        .join(ParkingZone, GuidanceDisplay.zone_id == ParkingZone.id)
        .order_by(GuidanceDisplay.code)
    )

    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)

    if is_active is not None:
        statement = statement.where(GuidanceDisplay.is_active == is_active)

    rows = (await db.execute(statement)).all()

    return [
        await get_display_message_by_display_async(db, display, zone)
        for display, zone in rows
    ]
