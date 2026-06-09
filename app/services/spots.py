from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.schemas.spots import SpotDetailResponse, SpotListItem, SpotListResponse


# Built-in default: new-format spot codes only (no legacy formats).
# Overridable via the DISABLED_SPOT_CODES env var (comma-separated).
_DEFAULT_DISABLED_SPOT_CODES = frozenset(
    {f"B1-B-01-{number}" for number in range(1, 7)}
    | {f"B1-B-02-{number}" for number in range(1, 5)}
)


def _parse_disabled_spot_codes(raw: str | None) -> frozenset[str]:
    if not raw:
        return _DEFAULT_DISABLED_SPOT_CODES
    return frozenset(code.strip() for code in raw.split(",") if code.strip())


DISABLED_SPOT_CODES = _parse_disabled_spot_codes(settings.disabled_spot_codes)


class AmbiguousSpotCodeError(Exception):
    def __init__(self, spot_code: str) -> None:
        self.spot_code = spot_code
        super().__init__(f"Spot code '{spot_code}' matches multiple spots.")


def _base_spots_statement():
    return (
        select(
            ParkingSector.code.label("sector_code"),
            ParkingZone.code.label("camera_zone_code"),
            ParkingSpot.code.label("spot_code"),
            ParkingSpot.status.label("status"),
            ParkingSpot.is_active.label("is_active"),
        )
        .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
        .join(ParkingSector, ParkingZone.sector_id == ParkingSector.id)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingFloor.is_active.is_(True),
            ParkingSector.is_active.is_(True),
            ParkingZone.is_active.is_(True),
        )
    )


def _list_spots_statement(
    *,
    status: SpotStatus | None,
    sector_code: str | None,
):
    statement = _base_spots_statement().order_by(
        ParkingZone.code,
        ParkingSector.code,
        ParkingZone.code,
        ParkingSpot.sort_order,
        ParkingSpot.code,
    )

    if status is not None:
        statement = statement.where(ParkingSpot.status == status.value)

    if sector_code is not None:
        statement = statement.where(ParkingSector.code == sector_code)

    return statement


def _spot_list_response(rows) -> SpotListResponse:
    return SpotListResponse(
        items=[
            SpotListItem(
                sector_code=row.sector_code,
                camera_zone_code=row.camera_zone_code,
                spot_code=row.spot_code,
                status=row.status,
                is_active=row.is_active,
                is_disabled=_is_disabled_spot(row.spot_code),
            )
            for row in rows
        ]
    )


def list_spots(
    db: Session,
    *,
    status: SpotStatus | None = None,
    sector_code: str | None = None,
) -> SpotListResponse:
    rows = db.execute(
        _list_spots_statement(status=status, sector_code=sector_code)
    ).all()
    return _spot_list_response(rows)


async def list_spots_async(
    db: AsyncSession,
    *,
    status: SpotStatus | None = None,
    sector_code: str | None = None,
) -> SpotListResponse:
    rows = (
        await db.execute(_list_spots_statement(status=status, sector_code=sector_code))
    ).all()
    return _spot_list_response(rows)


def _get_spot_statement(
    spot_code: str,
    *,
    sector_code: str | None,
    camera_zone_code: str | None,
):
    statement = _base_spots_statement().where(ParkingSpot.code == spot_code)

    if sector_code is not None:
        statement = statement.where(ParkingSector.code == sector_code)

    if camera_zone_code is not None:
        statement = statement.where(ParkingZone.code == camera_zone_code)

    return statement


def _spot_detail_from_rows(rows, spot_code: str) -> SpotDetailResponse | None:
    if len(rows) > 1:
        raise AmbiguousSpotCodeError(spot_code)

    row = rows[0] if rows else None
    if row is None:
        return None

    return SpotDetailResponse(
        sector_code=row.sector_code,
        camera_zone_code=row.camera_zone_code,
        spot_code=row.spot_code,
        status=row.status,
        is_active=row.is_active,
        is_disabled=_is_disabled_spot(row.spot_code),
    )


def get_spot_by_code(
    db: Session,
    spot_code: str,
    *,
    sector_code: str | None = None,
    camera_zone_code: str | None = None,
) -> SpotDetailResponse | None:
    rows = db.execute(
        _get_spot_statement(
            spot_code, sector_code=sector_code, camera_zone_code=camera_zone_code
        )
    ).all()
    return _spot_detail_from_rows(rows, spot_code)


async def get_spot_by_code_async(
    db: AsyncSession,
    spot_code: str,
    *,
    sector_code: str | None = None,
    camera_zone_code: str | None = None,
) -> SpotDetailResponse | None:
    rows = (
        await db.execute(
            _get_spot_statement(
                spot_code, sector_code=sector_code, camera_zone_code=camera_zone_code
            )
        )
    ).all()
    return _spot_detail_from_rows(rows, spot_code)


def _resolve_spot_statement(
    *,
    spot_code: str,
    sector_code: str | None,
    camera_zone_code: str | None,
):
    statement = (
        select(ParkingSpot)
        .join(ParkingZone, ParkingSpot.zone_id == ParkingZone.id)
        .join(ParkingSector, ParkingZone.sector_id == ParkingSector.id)
        .join(ParkingFloor, ParkingSector.floor_id == ParkingFloor.id)
        .where(
            ParkingSpot.code == spot_code,
            ParkingSpot.is_active.is_(True),
            ParkingZone.is_active.is_(True),
            ParkingSector.is_active.is_(True),
            ParkingFloor.is_active.is_(True),
        )
    )

    if sector_code is not None:
        statement = statement.where(ParkingSector.code == sector_code)

    if camera_zone_code is not None:
        statement = statement.where(ParkingZone.code == camera_zone_code)

    return statement.order_by(ParkingSpot.is_active.desc(), ParkingSpot.id.desc())


def _resolve_spot_from_results(
    spots,
    *,
    spot_code: str,
    camera_zone_code: str | None,
) -> ParkingSpot | None:
    if len(spots) > 1:
        if camera_zone_code is not None:
            return spots[0]
        raise AmbiguousSpotCodeError(spot_code)

    if not spots:
        return None

    return spots[0]


def resolve_spot(
    db: Session,
    *,
    spot_code: str,
    sector_code: str | None = None,
    camera_zone_code: str | None = None,
) -> ParkingSpot | None:
    spots = db.scalars(
        _resolve_spot_statement(
            spot_code=spot_code,
            sector_code=sector_code,
            camera_zone_code=camera_zone_code,
        )
    ).all()
    return _resolve_spot_from_results(
        spots, spot_code=spot_code, camera_zone_code=camera_zone_code
    )


def _is_disabled_spot(spot_code: str) -> bool:
    return spot_code in DISABLED_SPOT_CODES


async def resolve_spot_async(
    db: AsyncSession,
    *,
    spot_code: str,
    sector_code: str | None = None,
    camera_zone_code: str | None = None,
) -> ParkingSpot | None:
    spots = (
        await db.scalars(
            _resolve_spot_statement(
                spot_code=spot_code,
                sector_code=sector_code,
                camera_zone_code=camera_zone_code,
            )
        )
    ).all()
    return _resolve_spot_from_results(
        spots, spot_code=spot_code, camera_zone_code=camera_zone_code
    )
