import pytest

from app.services.spots import (
    AmbiguousSpotCodeError,
    get_spot_by_code,
    list_spots,
    resolve_spot,
)

from tests.conftest import seed_spot, seed_sector_with_camera_zone


def test_resolve_spot_returns_unique_spot(db_session):
    _, camera_zone = seed_sector_with_camera_zone(db_session)
    expected = seed_spot(db_session, camera_zone, code="A-001")
    db_session.commit()

    spot = resolve_spot(db_session, spot_code="A-001")

    assert spot is not None
    assert spot.id == expected.id


def test_resolve_spot_requires_scope_for_duplicate_codes(db_session):
    _, camera_zone_a = seed_sector_with_camera_zone(db_session, sector_code="A", camera_zone_code="A1")
    _, camera_zone_b = seed_sector_with_camera_zone(db_session, sector_code="B", camera_zone_code="B1")
    seed_spot(db_session, camera_zone_a, code="001")
    seed_spot(db_session, camera_zone_b, code="001")
    db_session.commit()

    with pytest.raises(AmbiguousSpotCodeError):
        resolve_spot(db_session, spot_code="001")

    spot = resolve_spot(db_session, spot_code="001", sector_code="B")
    assert spot is not None
    assert spot.zone_id == camera_zone_b.id


def test_get_spot_by_code_returns_detail_with_optional_scope(db_session):
    _, camera_zone = seed_sector_with_camera_zone(db_session)
    seed_spot(db_session, camera_zone, code="A-001", status="OCCUPIED")
    db_session.commit()

    spot = get_spot_by_code(db_session, "A-001", sector_code="A")

    assert spot is not None
    assert spot.sector_code == "A"
    assert spot.camera_zone_code == "A1"
    assert spot.status == "OCCUPIED"


def test_list_spots_marks_disabled_parking_places(db_session):
    _, camera_zone_01 = seed_sector_with_camera_zone(
        db_session, sector_code="B1-B", camera_zone_code="B1-B-01"
    )
    _, camera_zone_03 = seed_sector_with_camera_zone(
        db_session, sector_code="B1-B", camera_zone_code="B1-B-03"
    )
    seed_spot(db_session, camera_zone_01, code="B1-B-01-1", status="FREE")
    seed_spot(db_session, camera_zone_03, code="B1-B-03-1", status="FREE")
    db_session.commit()

    response = list_spots(db_session, sector_code="B1-B")

    by_code = {item.spot_code: item.is_disabled for item in response.items}
    assert by_code["B1-B-01-1"] is True
    assert by_code["B1-B-03-1"] is False
