import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import GuidanceDisplay, ParkingFloor, ParkingSector, ParkingSpot, ParkingZone


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    with SessionLocal() as db:
        yield db

    Base.metadata.drop_all(engine)


def seed_zone_with_row(
    db,
    *,
    zone_code: str = "A",
    row_code: str = "A1",
) -> tuple[ParkingSector, ParkingZone]:
    floor_code = zone_code.split("-", maxsplit=1)[0] if "-" in zone_code else "P1"
    floor = db.query(ParkingFloor).filter_by(code=floor_code).one_or_none()
    if floor is None:
        floor = ParkingFloor(
            title=f"Floor {floor_code}",
            code=floor_code,
            sort_order=1,
            is_active=True,
        )
        db.add(floor)
        db.flush()

    sector = ParkingSector(
        floor_id=floor.id,
        title=f"Sector {zone_code}",
        code=zone_code,
        sector_letter=zone_code.split("-", maxsplit=1)[-1],
        sort_order=1,
        is_active=True,
    )
    db.add(sector)
    db.flush()

    zone = ParkingZone(
        sector_id=sector.id,
        title=f"Camera Zone {row_code}",
        code=row_code,
        zone_number=row_code.rsplit("-", maxsplit=1)[-1],
        sort_order=1,
        is_active=True,
    )
    db.add(zone)
    db.flush()

    return sector, zone


def seed_spot(
    db,
    row: ParkingZone,
    *,
    code: str,
    status: str = "FREE",
    sort_order: int = 1,
) -> ParkingSpot:
    spot = ParkingSpot(
        zone_id=row.id,
        code=code,
        status=status,
        sort_order=sort_order,
        is_active=True,
    )
    db.add(spot)
    db.flush()
    return spot


def seed_display(
    db,
    zone: ParkingSector,
    *,
    code: str = "DISP-A-01",
    arrow_direction: str = "AHEAD",
    is_active: bool = True,
) -> GuidanceDisplay:
    display = GuidanceDisplay(
        title="Display",
        code=code,
        sector_id=zone.id,
        arrow_direction=arrow_direction,
        is_active=is_active,
    )
    db.add(display)
    db.flush()
    return display
