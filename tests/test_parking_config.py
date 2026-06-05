import pytest

from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.services.parking_config import (
    expand_spot_range,
    parse_sector_spec,
    seed_sector_display_config,
    seed_sector_spots,
)


def test_expand_spot_range_preserves_padding():
    assert expand_spot_range("B1-C-01-1..B1-C-01-3") == [
        "B1-C-01-1",
        "B1-C-01-2",
        "B1-C-01-3",
    ]


def test_expand_spot_range_supports_short_padding():
    assert expand_spot_range("B2-C01..B2-C03") == [
        "B2-C01",
        "B2-C02",
        "B2-C03",
    ]


def test_expand_spot_range_rejects_mismatched_prefix():
    with pytest.raises(ValueError):
        expand_spot_range("B1-C001..B2-C003")


def test_parse_sector_spec_returns_sector_and_spots():
    sector_code, spot_codes = parse_sector_spec("B1-C=B1-C-01-1..B1-C-01-2")

    assert sector_code == "B1-C"
    assert spot_codes == ["B1-C-01-1", "B1-C-01-2"]


def test_seed_sector_display_config_creates_base_config_without_spots(db_session):
    result = seed_sector_display_config(
        db_session,
        sector_codes=["B1-A", "B1-B", "B1-C"],
    )

    assert result.floors_created == 1
    assert result.sectors_created == 3
    assert result.displays_created == 3
    assert db_session.query(ParkingFloor).count() == 1
    assert db_session.query(ParkingSector).count() == 3
    assert db_session.query(GuidanceDisplay).count() == 3
    assert db_session.query(ParkingSpot).count() == 0


def test_seed_sector_display_config_is_idempotent(db_session):
    seed_sector_display_config(
        db_session,
        sector_codes=["B1-A", "B1-B", "B1-C"],
    )
    result = seed_sector_display_config(
        db_session,
        sector_codes=["B1-A", "B1-B", "B1-C"],
    )

    assert result.floors_created == 0
    assert result.sectors_created == 0
    assert result.displays_created == 0
    assert db_session.query(ParkingFloor).count() == 1
    assert db_session.query(ParkingSector).count() == 3
    assert db_session.query(GuidanceDisplay).count() == 3


def test_seed_sector_spots_creates_config(db_session):
    result = seed_sector_spots(
        db_session,
        sector_code="B1-C",
        spot_codes=["B1-C-01-1", "B1-C-01-2"],
        initial_status=SpotStatus.UNKNOWN,
    )

    sector = db_session.query(ParkingSector).filter_by(code="B1-C").one()
    zone = db_session.query(ParkingZone).filter_by(sector_id=sector.id, code="B1-C-01").one()
    spots = db_session.query(ParkingSpot).filter_by(zone_id=zone.id).all()
    display = db_session.query(GuidanceDisplay).filter_by(code="DISP-B1-C").one()

    assert result.zones_created == 1
    assert result.spots_created == 2
    assert result.displays_created == 1
    assert [spot.code for spot in spots] == ["B1-C-01-1", "B1-C-01-2"]
    assert {spot.status for spot in spots} == {"UNKNOWN"}
    assert display.sector_id == sector.id


def test_seed_sector_spots_is_idempotent(db_session):
    seed_sector_spots(
        db_session,
        sector_code="B1-C",
        spot_codes=["B1-C-01-1", "B1-C-01-2"],
    )
    result = seed_sector_spots(
        db_session,
        sector_code="B1-C",
        spot_codes=["B1-C-01-1", "B1-C-01-2"],
    )

    assert result.zones_created == 0
    assert result.spots_created == 0
    assert result.displays_created == 0
    assert db_session.query(ParkingSector).count() == 1
    assert db_session.query(ParkingZone).count() == 1
    assert db_session.query(ParkingSpot).count() == 2
    assert db_session.query(GuidanceDisplay).count() == 1


def test_seed_sector_spots_can_update_existing_status(db_session):
    seed_sector_spots(
        db_session,
        sector_code="B1-C",
        spot_codes=["B1-C-01-1", "B1-C-01-2"],
        initial_status=SpotStatus.UNKNOWN,
    )

    result = seed_sector_spots(
        db_session,
        sector_code="B1-C",
        spot_codes=["B1-C-01-1", "B1-C-01-2"],
        initial_status=SpotStatus.FREE,
        update_existing_status=True,
    )

    spots = db_session.query(ParkingSpot).order_by(ParkingSpot.code).all()

    assert result.spots_created == 0
    assert result.spots_updated == 2
    assert [spot.status for spot in spots] == ["FREE", "FREE"]
