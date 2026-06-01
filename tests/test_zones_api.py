from app.api.v1.zones import get_zone_summary, get_zones_summary

from tests.conftest import seed_spot, seed_zone_with_row


def test_get_zone_summary_includes_unknown_and_offline(db_session):
    _, row = seed_zone_with_row(db_session)
    seed_spot(db_session, row, code="A-001", status="FREE")
    seed_spot(db_session, row, code="A-002", status="OCCUPIED")
    seed_spot(db_session, row, code="A-003", status="OFFLINE")
    seed_spot(db_session, row, code="A-004", status="UNKNOWN")
    db_session.commit()

    summary = get_zone_summary("A", db_session)

    assert summary.total_spots == 4
    assert summary.free_spots == 1
    assert summary.occupied_spots == 1
    assert summary.offline_spots == 1
    assert summary.unknown_spots == 1


def test_get_zones_summary_includes_unknown_and_offline(db_session):
    _, row = seed_zone_with_row(db_session)
    seed_spot(db_session, row, code="A-001", status="FREE")
    seed_spot(db_session, row, code="A-002", status="UNKNOWN")
    db_session.commit()

    response = get_zones_summary(db_session)

    assert len(response.items) == 1
    assert response.items[0].total_spots == 2
    assert response.items[0].free_spots == 1
    assert response.items[0].occupied_spots == 0
    assert response.items[0].offline_spots == 0
    assert response.items[0].unknown_spots == 1
