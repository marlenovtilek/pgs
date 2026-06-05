from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.use_cases.calculate_zone_summary import calculate_zone_summary
from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.zone_summary import ZoneSummaryItem


def get_zone_summary_item(db: Session, sector_code: str) -> ZoneSummaryItem | None:
    sector = db.scalar(
        select(ParkingSector)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.code == sector_code,
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
    )
    if sector is None:
        return None

    rows = db.execute(
        select(ParkingSpot.status)
        .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
        .where(
            ParkingZone.sector_id == sector.id,
            ParkingZone.is_active.is_(True),
            ParkingSpot.is_active.is_(True),
        )
    ).all()

    summary = calculate_zone_summary([SpotStatus(row.status) for row in rows])

    return ZoneSummaryItem(
        sector_code=sector.code,
        sector_title=sector.title,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
        offline_spots=summary["offline"],
        unknown_spots=summary["unknown"],
    )


async def get_zone_summary_item_async(
    db: AsyncSession,
    sector_code: str,
) -> ZoneSummaryItem | None:
    sector = await db.scalar(
        select(ParkingSector)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSector.code == sector_code,
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
    )
    if sector is None:
        return None

    rows = (
        await db.execute(
            select(ParkingSpot.status)
            .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
            .where(
                ParkingZone.sector_id == sector.id,
                ParkingZone.is_active.is_(True),
                ParkingSpot.is_active.is_(True),
            )
        )
    ).all()

    summary = calculate_zone_summary([SpotStatus(row.status) for row in rows])

    return ZoneSummaryItem(
        sector_code=sector.code,
        sector_title=sector.title,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
        offline_spots=summary["offline"],
        unknown_spots=summary["unknown"],
    )


def list_zone_summary_items(db: Session) -> list[ZoneSummaryItem]:
    statement = (
        select(
            ParkingSector.code.label("sector_code"),
            ParkingSector.title.label("sector_title"),
            func.count(ParkingSpot.id).label("total_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.FREE.value, 1), else_=0)
            ).label("free_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.OCCUPIED.value, 1), else_=0)
            ).label("occupied_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.OFFLINE.value, 1), else_=0)
            ).label("offline_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.UNKNOWN.value, 1), else_=0)
            ).label("unknown_spots"),
        )
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .join(ParkingZone, ParkingZone.sector_id == ParkingSector.id)
        .join(ParkingSpot, ParkingSpot.zone_id == ParkingZone.id)
        .where(
            ParkingFloor.is_active.is_(True),
            ParkingSector.is_active.is_(True),
            ParkingZone.is_active.is_(True),
            ParkingSpot.is_active.is_(True),
        )
        .group_by(ParkingSector.id, ParkingSector.code, ParkingSector.title)
        .order_by(ParkingSector.code)
    )

    rows = db.execute(statement).all()

    return [
        ZoneSummaryItem(
            sector_code=row.sector_code,
            sector_title=row.sector_title,
            total_spots=row.total_spots,
            free_spots=row.free_spots or 0,
            occupied_spots=row.occupied_spots or 0,
            offline_spots=row.offline_spots or 0,
            unknown_spots=row.unknown_spots or 0,
        )
        for row in rows
    ]


async def list_zone_summary_items_async(db: AsyncSession) -> list[ZoneSummaryItem]:
    statement = (
        select(
            ParkingSector.code.label("sector_code"),
            ParkingSector.title.label("sector_title"),
            func.count(ParkingSpot.id).label("total_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.FREE.value, 1), else_=0)
            ).label("free_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.OCCUPIED.value, 1), else_=0)
            ).label("occupied_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.OFFLINE.value, 1), else_=0)
            ).label("offline_spots"),
            func.sum(
                case((ParkingSpot.status == SpotStatus.UNKNOWN.value, 1), else_=0)
            ).label("unknown_spots"),
        )
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .join(ParkingZone, ParkingZone.sector_id == ParkingSector.id)
        .join(ParkingSpot, ParkingSpot.zone_id == ParkingZone.id)
        .where(
            ParkingFloor.is_active.is_(True),
            ParkingSector.is_active.is_(True),
            ParkingZone.is_active.is_(True),
            ParkingSpot.is_active.is_(True),
        )
        .group_by(ParkingSector.id, ParkingSector.code, ParkingSector.title)
        .order_by(ParkingSector.code)
    )

    rows = (await db.execute(statement)).all()

    return [
        ZoneSummaryItem(
            sector_code=row.sector_code,
            sector_title=row.sector_title,
            total_spots=row.total_spots,
            free_spots=row.free_spots or 0,
            occupied_spots=row.occupied_spots or 0,
            offline_spots=row.offline_spots or 0,
            unknown_spots=row.unknown_spots or 0,
        )
        for row in rows
    ]


__all__ = [
    "calculate_zone_summary",
    "get_zone_summary_item",
    "get_zone_summary_item_async",
    "list_zone_summary_items",
    "list_zone_summary_items_async",
]
