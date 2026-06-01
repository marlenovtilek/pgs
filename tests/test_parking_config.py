import pytest

from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.services.parking_config import (
    expand_spot_range,
    parse_zone_spec,
    seed_zone_spots,
)


def test_expand_spot_range_preserves_padding():
    assert expand_spot_range("B1-C001..B1-C003") == [
        "B1-C001",
        "B1-C002",
        "B1-C003",
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


def test_parse_zone_spec_returns_zone_and_spots():
    zone_code, spot_codes = parse_zone_spec("B1-C=B1-C001..B1-C002")

    assert zone_code == "B1-C"
    assert spot_codes == ["B1-C001", "B1-C002"]


def test_seed_zone_spots_creates_config(db_session):
    result = seed_zone_spots(
        db_session,
        zone_code="B1-C",
        spot_codes=["B1-C001", "B1-C002"],
        initial_status=SpotStatus.UNKNOWN,
    )

    zone = db_session.query(ParkingZone).filter_by(code="B1-C").one()
    row = db_session.query(ParkingRow).filter_by(zone_id=zone.id, code="B1-C").one()
    spots = db_session.query(ParkingSpot).filter_by(row_id=row.id).all()
    display = db_session.query(GuidanceDisplay).filter_by(code="DISP-B1-C").one()

    assert result.zones_created == 1
    assert result.rows_created == 1
    assert result.spots_created == 2
    assert result.displays_created == 1
    assert [spot.code for spot in spots] == ["B1-C001", "B1-C002"]
    assert {spot.status for spot in spots} == {"UNKNOWN"}
    assert display.zone_id == zone.id


def test_seed_zone_spots_is_idempotent(db_session):
    seed_zone_spots(
        db_session,
        zone_code="B1-C",
        spot_codes=["B1-C001", "B1-C002"],
    )
    result = seed_zone_spots(
        db_session,
        zone_code="B1-C",
        spot_codes=["B1-C001", "B1-C002"],
    )

    assert result.zones_created == 0
    assert result.rows_created == 0
    assert result.spots_created == 0
    assert result.displays_created == 0
    assert db_session.query(ParkingZone).count() == 1
    assert db_session.query(ParkingRow).count() == 1
    assert db_session.query(ParkingSpot).count() == 2
    assert db_session.query(GuidanceDisplay).count() == 1
