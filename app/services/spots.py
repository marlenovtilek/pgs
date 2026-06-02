from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.spots import SpotDetailResponse, SpotListItem, SpotListResponse


class AmbiguousSpotCodeError(Exception):
    def __init__(self, spot_code: str) -> None:
        self.spot_code = spot_code
        super().__init__(f"Spot code '{spot_code}' matches multiple spots.")


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


async def list_spots_async(
    db: AsyncSession,
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

    rows = (await db.execute(statement)).all()

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


def get_spot_by_code(
    db: Session,
    spot_code: str,
    *,
    zone_code: str | None = None,
    row_code: str | None = None,
) -> SpotDetailResponse | None:
    statement = _base_spots_statement().where(ParkingSpot.code == spot_code)

    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)

    if row_code is not None:
        statement = statement.where(ParkingRow.code == row_code)

    rows = db.execute(statement).all()
    if len(rows) > 1:
        raise AmbiguousSpotCodeError(spot_code)

    row = rows[0] if rows else None
    if row is None:
        return None

    return SpotDetailResponse(
        zone_code=row.zone_code,
        row_code=row.row_code,
        spot_code=row.spot_code,
        status=row.status,
        is_active=row.is_active,
    )


async def get_spot_by_code_async(
    db: AsyncSession,
    spot_code: str,
    *,
    zone_code: str | None = None,
    row_code: str | None = None,
) -> SpotDetailResponse | None:
    statement = _base_spots_statement().where(ParkingSpot.code == spot_code)

    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)

    if row_code is not None:
        statement = statement.where(ParkingRow.code == row_code)

    rows = (await db.execute(statement)).all()
    if len(rows) > 1:
        raise AmbiguousSpotCodeError(spot_code)

    row = rows[0] if rows else None
    if row is None:
        return None

    return SpotDetailResponse(
        zone_code=row.zone_code,
        row_code=row.row_code,
        spot_code=row.spot_code,
        status=row.status,
        is_active=row.is_active,
    )


def resolve_spot(
    db: Session,
    *,
    spot_code: str,
    zone_code: str | None = None,
    row_code: str | None = None,
) -> ParkingSpot | None:
    statement = (
        select(ParkingSpot)
        .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
        .join(ParkingZone, ParkingRow.zone_id == ParkingZone.id)
        .where(ParkingSpot.code == spot_code)
    )

    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)

    if row_code is not None:
        statement = statement.where(ParkingRow.code == row_code)

    spots = db.scalars(statement).all()
    if len(spots) > 1:
        raise AmbiguousSpotCodeError(spot_code)

    if not spots:
        return None

    return spots[0]


async def resolve_spot_async(
    db: AsyncSession,
    *,
    spot_code: str,
    zone_code: str | None = None,
    row_code: str | None = None,
) -> ParkingSpot | None:
    statement = (
        select(ParkingSpot)
        .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
        .join(ParkingZone, ParkingRow.zone_id == ParkingZone.id)
        .where(ParkingSpot.code == spot_code)
    )

    if zone_code is not None:
        statement = statement.where(ParkingZone.code == zone_code)

    if row_code is not None:
        statement = statement.where(ParkingRow.code == row_code)

    spots = (await db.scalars(statement)).all()
    if len(spots) > 1:
        raise AmbiguousSpotCodeError(spot_code)

    if not spots:
        return None

    return spots[0]
