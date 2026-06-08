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


def seed_sector_with_camera_zone(
    db,
    *,
    sector_code: str = "A",
    camera_zone_code: str = "A1",
) -> tuple[ParkingSector, ParkingZone]:
    floor_code = sector_code.split("-", maxsplit=1)[0] if "-" in sector_code else "P1"
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

    sector = db.query(ParkingSector).filter_by(code=sector_code).one_or_none()
    if sector is None:
        sector = ParkingSector(
            floor_id=floor.id,
            title=f"Sector {sector_code}",
            code=sector_code,
            sector_letter=sector_code.split("-", maxsplit=1)[-1],
            sort_order=1,
            is_active=True,
        )
        db.add(sector)
        db.flush()

    zone = db.query(ParkingZone).filter_by(sector_id=sector.id, code=camera_zone_code).one_or_none()
    if zone is None:
        zone = ParkingZone(
            sector_id=sector.id,
            title=f"Camera Zone {camera_zone_code}",
            code=camera_zone_code,
            zone_number=camera_zone_code.rsplit("-", maxsplit=1)[-1],
            sort_order=1,
            is_active=True,
        )
        db.add(zone)
        db.flush()

    return sector, zone


def seed_spot(
    db,
    camera_zone: ParkingZone,
    *,
    code: str,
    status: str = "FREE",
    sort_order: int = 1,
) -> ParkingSpot:
    spot = ParkingSpot(
        zone_id=camera_zone.id,
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
    sector: ParkingSector,
    *,
    code: str = "DISP-A-01",
    arrow_direction: str = "AHEAD",
    camera_zones: list[ParkingZone] | None = None,
    is_active: bool = True,
) -> GuidanceDisplay:
    display = GuidanceDisplay(
        title="Display",
        code=code,
        sector_id=sector.id,
        arrow_direction=arrow_direction,
        is_active=is_active,
    )
    if camera_zones is None:
        camera_zones = db.query(ParkingZone).filter_by(sector_id=sector.id).all()
    display.zones = camera_zones
    db.add(display)
    db.flush()
    return display
