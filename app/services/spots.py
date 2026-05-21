from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.spots import SpotDetailResponse, SpotListItem, SpotListResponse


def _base_spots_statement():
    return (
        select(
            ParkingZone.code.label("zone_code"),
            ParkingRow.code.label("row_code"),
            ParkingSpot.code.label("spot_code"),
            ParkingSpot.status.label("status"),
            ParkingSpot.is_active.label("is_active"),
        )
        .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
        .join(ParkingZone, ParkingRow.zone_id == ParkingZone.id)
    )


def list_spots(
    db: Session,
    *,
    status: SpotStatus | None = None,
    zone_code: str | None = None,
) -> SpotListResponse:
    statement = _base_spots_statement().order_by(
        ParkingZone.code,
        ParkingRow.code,
        ParkingSpot.sort_order,
        ParkingSpot.code,
    )

    if status is not None:
        statement = statement.where(ParkingSpot.status == status.value)

    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)

    rows = db.execute(statement).all()

    items = [
        SpotListItem(
            zone_code=row.zone_code,
            row_code=row.row_code,
            spot_code=row.spot_code,
            status=row.status,
            is_active=row.is_active,
        )
        for row in rows
    ]

    return SpotListResponse(items=items)


def get_spot_by_code(db: Session, spot_code: str) -> SpotDetailResponse | None:
    statement = _base_spots_statement().where(ParkingSpot.code == spot_code).limit(1)

    row = db.execute(statement).first()
    if row is None:
        return None

    return SpotDetailResponse(
        zone_code=row.zone_code,
        row_code=row.row_code,
        spot_code=row.spot_code,
        status=row.status,
        is_active=row.is_active,
    )
