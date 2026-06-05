from app.services.zone_summary import get_zone_summary_item, list_zone_summary_items

from tests.conftest import seed_spot, seed_sector_with_camera_zone


def test_get_zone_summary_includes_unknown_and_offline(db_session):
    _, camera_zone = seed_sector_with_camera_zone(db_session)
    seed_spot(db_session, camera_zone, code="A-001", status="FREE")
    seed_spot(db_session, camera_zone, code="A-002", status="OCCUPIED")
    seed_spot(db_session, camera_zone, code="A-003", status="OFFLINE")
    seed_spot(db_session, camera_zone, code="A-004", status="UNKNOWN")
    db_session.commit()

    summary = get_zone_summary_item(db_session, "A")

    assert summary is not None
    assert summary.total_spots == 4
    assert summary.free_spots == 1
    assert summary.occupied_spots == 1
    assert summary.offline_spots == 1
    assert summary.unknown_spots == 1


def test_get_zones_summary_includes_unknown_and_offline(db_session):
    _, camera_zone = seed_sector_with_camera_zone(db_session)
    seed_spot(db_session, camera_zone, code="A-001", status="FREE")
    seed_spot(db_session, camera_zone, code="A-002", status="UNKNOWN")
    db_session.commit()

    items = list_zone_summary_items(db_session)

    assert len(items) == 1
    assert items[0].total_spots == 2
    assert items[0].free_spots == 1
    assert items[0].occupied_spots == 0
    assert items[0].offline_spots == 0
    assert items[0].unknown_spots == 1
