import pytest

from app.services.mqtt_reconciliation import (
    free_spots_from_payload,
    is_total_free_topic,
    reconcile_total_free_event,
    reconcile_zone_free_event,
    zone_id_from_topic,
)

from tests.conftest import seed_spot, seed_zone_with_row


def test_zone_id_from_topic_extracts_zone_id():
    assert zone_id_from_topic("parking/zones/B1-C/free") == "B1-C"


def test_zone_id_from_topic_rejects_other_topics():
    assert zone_id_from_topic("parking/spots/B1-C001/status") is None


def test_is_total_free_topic():
    assert is_total_free_topic("parking/total/free") is True
    assert is_total_free_topic("parking/zones/B1-C/free") is False


def test_free_spots_from_payload_requires_integer():
    assert free_spots_from_payload({"free_spots": 3}) == 3
    with pytest.raises(ValueError):
        free_spots_from_payload({"free_spots": "3"})


def test_reconcile_zone_free_event_returns_diff_and_unknowns(db_session):
    _, row = seed_zone_with_row(db_session, zone_code="B1-C", row_code="B1-C")
    seed_spot(db_session, row, code="B1-C001", status="FREE")
    seed_spot(db_session, row, code="B1-C002", status="OCCUPIED")
    seed_spot(db_session, row, code="B1-C003", status="UNKNOWN")
    db_session.commit()

    result = reconcile_zone_free_event(
        db_session,
        topic="parking/zones/B1-C/free",
        payload={"zone_id": "B1-C", "free_spots": 2},
    )

    assert result.zone_code == "B1-C"
    assert result.mqtt_free_spots == 2
    assert result.pgs_free_spots == 1
    assert result.diff == 1
    assert result.total_spots == 3
    assert result.occupied_spots == 1
    assert result.unknown_spots == 1
    assert result.offline_spots == 0


def test_reconcile_zone_free_event_handles_missing_zone(db_session):
    result = reconcile_zone_free_event(
        db_session,
        topic="parking/zones/MISSING/free",
        payload={"zone_id": "MISSING", "free_spots": 2},
    )

    assert result.zone_code == "MISSING"
    assert result.pgs_free_spots is None
    assert result.diff is None


def test_reconcile_total_free_event_returns_total_diff(db_session):
    _, row_a = seed_zone_with_row(db_session, zone_code="A", row_code="A")
    _, row_b = seed_zone_with_row(db_session, zone_code="B", row_code="B")
    seed_spot(db_session, row_a, code="A001", status="FREE")
    seed_spot(db_session, row_b, code="B001", status="FREE")
    seed_spot(db_session, row_b, code="B002", status="OCCUPIED")
    db_session.commit()

    result = reconcile_total_free_event(db_session, payload={"free_spots": 5})

    assert result.mqtt_free_spots == 5
    assert result.pgs_free_spots == 2
    assert result.diff == 3
