from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.spot_events import create_spot_event
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.schemas.spot_event import SpotEventRequest

from tests.conftest import seed_spot, seed_zone_with_row


def test_create_spot_event_updates_spot_and_stores_event(db_session):
    _, row = seed_zone_with_row(db_session)
    spot = seed_spot(db_session, row, code="A-001", status="FREE")
    db_session.commit()

    request = SpotEventRequest(
        spot_code="A-001",
        status="OCCUPIED",
        detected_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
    )

    response = create_spot_event(request, db_session)

    db_session.refresh(spot)
    event = db_session.scalar(select(SpotOccupancyEvent))

    assert response.success is True
    assert response.spot_code == "A-001"
    assert response.status == "OCCUPIED"
    assert spot.status == "OCCUPIED"
    assert event is not None
    assert event.spot_id == spot.id


def test_create_spot_event_is_idempotent_by_dedup_key(db_session):
    _, row = seed_zone_with_row(db_session)
    seed_spot(db_session, row, code="A-001", status="FREE")
    db_session.commit()

    request = SpotEventRequest(
        spot_code="A-001",
        status="OCCUPIED",
        detected_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
        event_id="evt-1",
    )

    first = create_spot_event(request, db_session)
    second = create_spot_event(request, db_session)
    events = db_session.scalars(select(SpotOccupancyEvent)).all()

    assert first.dedup_key == "UNV_SERVICE:evt-1"
    assert second.dedup_key == first.dedup_key
    assert len(events) == 1


def test_create_spot_event_rejects_ambiguous_spot_code(db_session):
    _, row_a = seed_zone_with_row(db_session, zone_code="A", row_code="A1")
    _, row_b = seed_zone_with_row(db_session, zone_code="B", row_code="B1")
    seed_spot(db_session, row_a, code="001")
    seed_spot(db_session, row_b, code="001")
    db_session.commit()

    request = SpotEventRequest(
        spot_code="001",
        status="OCCUPIED",
        detected_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(HTTPException) as exc_info:
        create_spot_event(request, db_session)

    assert exc_info.value.status_code == 409
