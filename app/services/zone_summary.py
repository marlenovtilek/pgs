from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.domain.use_cases.calculate_zone_summary import calculate_zone_summary
from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.zone_summary import ZoneSummaryItem


def get_zone_summary_item(db: Session, zone_code: str) -> ZoneSummaryItem | None:
    zone = db.scalar(select(ParkingZone).where(ParkingZone.code == zone_code))
    if zone is None:
        return None

    rows = db.execute(
        select(ParkingSpot.status)
        .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
        .where(ParkingRow.zone_id == zone.id)
    ).all()

    summary = calculate_zone_summary([SpotStatus(row.status) for row in rows])

    return ZoneSummaryItem(
        zone_code=zone.code,
        zone_title=zone.title,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
        offline_spots=summary["offline"],
        unknown_spots=summary["unknown"],
    )


def list_zone_summary_items(db: Session) -> list[ZoneSummaryItem]:
    statement = (
        select(
            ParkingZone.code.label("zone_code"),
            ParkingZone.title.label("zone_title"),
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
        .join(ParkingRow, ParkingRow.zone_id == ParkingZone.id)
        .join(ParkingSpot, ParkingSpot.row_id == ParkingRow.id)
        .group_by(ParkingZone.id, ParkingZone.code, ParkingZone.title)
        .order_by(ParkingZone.code)
    )

    rows = db.execute(statement).all()

    return [
        ZoneSummaryItem(
            zone_code=row.zone_code,
            zone_title=row.zone_title,
            total_spots=row.total_spots,
            free_spots=row.free_spots or 0,
            occupied_spots=row.occupied_spots or 0,
            offline_spots=row.offline_spots or 0,
            unknown_spots=row.unknown_spots or 0,
        )
        for row in rows
    ]


__all__ = ["calculate_zone_summary", "get_zone_summary_item", "list_zone_summary_items"]
