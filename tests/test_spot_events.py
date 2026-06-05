from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.adapters.led.mock import MockLedDisplayAdapter
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.schemas.spot_event import SpotEventRequest
from app.services.spot_events import process_spot_event
from app.services.spots import AmbiguousSpotCodeError

from tests.conftest import seed_display, seed_spot, seed_sector_with_camera_zone


def test_create_spot_event_updates_spot_and_stores_event(db_session):
    zone, camera_zone = seed_sector_with_camera_zone(db_session)
    spot = seed_spot(db_session, camera_zone, code="A-001", status="FREE")
    seed_display(db_session, zone)
    db_session.commit()

    request = SpotEventRequest(
        spot_code="A-001",
        status="OCCUPIED",
        detected_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
    )
    adapter = MockLedDisplayAdapter()

    result = process_spot_event(db_session, request, display_port=adapter)

    db_session.refresh(spot)
    event = db_session.scalar(select(SpotOccupancyEvent))

    response = result.response
    assert response.success is True
    assert response.spot_code == "A-001"
    assert response.status == "OCCUPIED"
    assert spot.status == "OCCUPIED"
    assert event is not None
    assert event.spot_id == spot.id
    assert result.led_commands_sent == 1
    assert adapter.commands[0].message == "A AHEAD 0"
    assert adapter.commands[0].display_text == "AHEAD 0 P"


def test_create_spot_event_is_idempotent_by_dedup_key(db_session):
    zone, camera_zone = seed_sector_with_camera_zone(db_session)
    seed_spot(db_session, camera_zone, code="A-001", status="FREE")
    seed_display(db_session, zone)
    db_session.commit()

    request = SpotEventRequest(
        spot_code="A-001",
        status="OCCUPIED",
        detected_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
        event_id="evt-1",
    )
    adapter = MockLedDisplayAdapter()

    first = process_spot_event(db_session, request, display_port=adapter)
    second = process_spot_event(db_session, request, display_port=adapter)
    events = db_session.scalars(select(SpotOccupancyEvent)).all()

    assert first.response.dedup_key == "UNV_SERVICE:evt-1"
    assert second.response.dedup_key == first.response.dedup_key
    assert first.led_commands_sent == 1
    assert second.led_commands_sent == 0
    assert len(adapter.commands) == 1
    assert len(events) == 1


def test_create_spot_event_rejects_ambiguous_spot_code(db_session):
    _, camera_zone_a = seed_sector_with_camera_zone(db_session, sector_code="A", camera_zone_code="A1")
    _, camera_zone_b = seed_sector_with_camera_zone(db_session, sector_code="B", camera_zone_code="B1")
    seed_spot(db_session, camera_zone_a, code="001")
    seed_spot(db_session, camera_zone_b, code="001")
    db_session.commit()

    request = SpotEventRequest(
        spot_code="001",
        status="OCCUPIED",
        detected_at=datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(AmbiguousSpotCodeError):
        process_spot_event(request=request, db=db_session)
