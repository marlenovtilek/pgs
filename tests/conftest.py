import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import GuidanceDisplay, ParkingRow, ParkingSpot, ParkingZone


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
) -> tuple[ParkingZone, ParkingRow]:
    zone = ParkingZone(
        title=f"Zone {zone_code}",
        code=zone_code,
        level="P1",
        is_active=True,
    )
    db.add(zone)
    db.flush()

    row = ParkingRow(
        zone_id=zone.id,
        title=f"Row {row_code}",
        code=row_code,
        sort_order=1,
        is_active=True,
    )
    db.add(row)
    db.flush()

    return zone, row


def seed_spot(
    db,
    row: ParkingRow,
    *,
    code: str,
    status: str = "FREE",
    sort_order: int = 1,
) -> ParkingSpot:
    spot = ParkingSpot(
        row_id=row.id,
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
    zone: ParkingZone,
    *,
    code: str = "DISP-A-01",
    arrow_direction: str = "AHEAD",
    is_active: bool = True,
) -> GuidanceDisplay:
    display = GuidanceDisplay(
        title="Display",
        code=code,
        zone_id=zone.id,
        arrow_direction=arrow_direction,
        is_active=is_active,
    )
    db.add(display)
    db.flush()
    return display
