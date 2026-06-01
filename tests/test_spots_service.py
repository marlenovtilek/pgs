import pytest

from app.services.spots import AmbiguousSpotCodeError, get_spot_by_code, resolve_spot

from tests.conftest import seed_spot, seed_zone_with_row


def test_resolve_spot_returns_unique_spot(db_session):
    _, row = seed_zone_with_row(db_session)
    expected = seed_spot(db_session, row, code="A-001")
    db_session.commit()

    spot = resolve_spot(db_session, spot_code="A-001")

    assert spot is not None
    assert spot.id == expected.id


def test_resolve_spot_requires_scope_for_duplicate_codes(db_session):
    _, row_a = seed_zone_with_row(db_session, zone_code="A", row_code="A1")
    _, row_b = seed_zone_with_row(db_session, zone_code="B", row_code="B1")
    seed_spot(db_session, row_a, code="001")
    seed_spot(db_session, row_b, code="001")
    db_session.commit()

    with pytest.raises(AmbiguousSpotCodeError):
        resolve_spot(db_session, spot_code="001")

    spot = resolve_spot(db_session, spot_code="001", zone_code="B")
    assert spot is not None
    assert spot.row_id == row_b.id


def test_get_spot_by_code_returns_detail_with_optional_scope(db_session):
    _, row = seed_zone_with_row(db_session)
    seed_spot(db_session, row, code="A-001", status="OCCUPIED")
    db_session.commit()

    spot = get_spot_by_code(db_session, "A-001", zone_code="A")

    assert spot is not None
    assert spot.zone_code == "A"
    assert spot.row_code == "A1"
    assert spot.status == "OCCUPIED"
